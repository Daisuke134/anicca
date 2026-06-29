#!/usr/bin/env bash
# earn/clip-promote — promote.fun USDC-Solana per-view clipping SLOT entrypoint (run-skill.mjs spawns
# this each wake). Does EXACTLY ONE bounded state-machine transition per wake (idempotent), prints ONE
# structured JSON line on stdout, exit 0. NO HUMAN: captcha→CapSolver, OTP→gog gmail, login→stored creds.
#
# Slot contract (REQ-12): one bounded transition chosen by the PURE decide(state,now); ONE line out.
# Watchdog (REQ-9): every browser/IO step is wrapped in a portable timeout; if a step blocks on human
# input it trips → did:"blocked:human:<step>" exit 0 (a recorded defect, NEVER a hang).
# DONE (REQ-8): the RECORD transition is the ONLY one that prints earned_usdc>0, via record-payout.mjs
# run under `env -i` (no PII) so the malice-guard passes.
set -uo pipefail
SK="$HOME/anicca/skills/earn/clip-promote"
PY=/opt/homebrew/bin/python3
NODE=/opt/homebrew/bin/node
[ -x "$NODE" ] || NODE=node
[ -x "$PY" ] || PY=python3

# env (own-identity only; PII is NOT scrubbed by the harness — we keep it out of the RECORD subprocess).
set -a; . "$HOME/.openclaw/.env" 2>/dev/null || true; set +a

EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-$(date -u +%s)}"
STEP_DEADLINE_S="${STEP_DEADLINE_S:-120}"
SOLANA_RPC_URL="${SOLANA_RPC_URL:-https://api.mainnet-beta.solana.com}"
WALLET="${CLIP_WALLET_SOLANA:-xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H}"
STATE="${CLIP_PROMOTE_STATE:-$HOME/.cloak/clip-promote-state.json}"
LEDGER="${EARN_LEDGER:-$HOME/.openclaw/state/clip-earn-ledger.jsonl}"
ACCTS="${CLIP_ACCOUNTS:-$HOME/.cloak/clip-accounts.json}"
CDP_DIR="${CDP_DIR:-$HOME/.claude/skills/ig-account-create/scripts}"
mkdir -p "$(dirname "$STATE")" "$(dirname "$LEDGER")" 2>/dev/null || true

# shared emit / run_step (portable watchdog, FIND-302) / blocked_or (fail-closed) — see _lib.sh.
. "$SK/_lib.sh"

# load the current pipeline state (missing ⇒ {} ⇒ decide returns SELECT).
read_state() { [ -f "$STATE" ] && cat "$STATE" || echo '{}'; }
NOW="$(date -u +%s)"
TRANS="$("$PY" -c "import json,sys;sys.path.insert(0,'$SK');from decide import decide;print(decide(json.loads(sys.stdin.read() or '{}'),$NOW))" <<<"$(read_state)" 2>/dev/null)"
[ -z "$TRANS" ] && TRANS="SELECT"   # decide failure ⇒ safe SELECT, never a dead-end

# discover mode: report the transition this wake WOULD run; take NO side effect (not a fake run — it
# claims no earn/post; it is how the loop inspects state).
if [ "$EARN_MODE" != "execute" ]; then
  emit "discover: would run transition=$TRANS (state=$STATE)"; exit 0
fi

# ── execute mode: run exactly the ONE transition. The live browser/promote.fun steps (SELECT/CLIP/POST/
#    SUBMIT/WITHDRAW) are wired in #14 against real infra; each is wrapped in run_step so a human-blocking
#    step trips the watchdog. RECORD is fully implemented (the DONE gate). ──
case "$TRANS" in
  RECORD)
    SIG="$("$PY" -c "import json;print((json.load(open('$STATE')) if __import__('os').path.exists('$STATE') else {}).get('sig',''))" 2>/dev/null)"
    if [ -z "$SIG" ]; then emit "record:no-sig"; exit 0; fi
    # env -i (FIND-301): the RECORD subprocess gets ONLY public wallet/RPC/ledger — no PII var reaches
    # the malice-guard in record.mjs.
    RES="$(run_step "$STEP_DEADLINE_S" env -i PATH="$PATH" HOME="$HOME" \
            SOLANA_RPC_URL="$SOLANA_RPC_URL" SIG="$SIG" WALLET="$WALLET" \
            EARN_LEDGER="$LEDGER" WAKE_ID="$WAKE" \
            "$NODE" "$SK/record-payout.mjs" 2>/dev/null)"; rc=$?
    blocked_or "record" "$rc" "record:step-failed"
    EARNED="$("$PY" -c "import json,sys;d=json.loads(sys.argv[1] or '{}');print(d.get('earn_usdc',0) if d.get('status')=='recorded' else 0)" "$RES" 2>/dev/null)"
    STATUS="$("$PY" -c "import json,sys;print(json.loads(sys.argv[1] or '{}').get('status','?'))" "$RES" 2>/dev/null)"
    if [ "$STATUS" = "recorded" ]; then
      # DONE: free the slot for the next campaign on the next wake.
      "$PY" -c "import json;json.dump({'phase':'idle'},open('$STATE','w'))" 2>/dev/null || true
      emit "record:DONE sig=$SIG" "${EARNED:-0}" 0; exit 0
    fi
    emit "record:$STATUS"; exit 0
    ;;
  SELECT)
    # REQ-1: fetch ACTIVE campaigns from the logged-in promote.fun tab + rank by cpm*budget; pick the top
    # not-yet-clipped, advance state to CLIP. REQ-1a: none eligible → narrate idle.
    PF_PORT="${CLIP_PROMOTE_CDP_PORT:-9222}"
    PF_TID="$(curl -sS --max-time 5 "http://localhost:$PF_PORT/json/list" 2>/dev/null | "$PY" -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
print(next((t['id'] for t in d if t.get('type')=='page' and 'promote.fun' in (t.get('url') or '')),''))" 2>/dev/null)"
    if [ -z "$PF_TID" ]; then emit "select:no-promote-tab (login session not open on :$PF_PORT)"; exit 0; fi
    CLIPPED="$("$PY" -c "import json,os;p='$STATE';d=json.load(open(p)) if os.path.exists(p) else {};print(','.join(d.get('clipped',[])))" 2>/dev/null)"
    RANKED="$(run_step "$STEP_DEADLINE_S" env CDP_DIR="$CDP_DIR" PF_TID="$PF_TID" CDP_PORT="$PF_PORT" \
              "$PY" "$SK/select_campaigns.py" 2>/dev/null)"; rc=$?
    blocked_or "select" "$rc" "select:fetch-failed"
    PICK="$("$PY" -c "import json,sys
r=json.loads(sys.argv[1] or '[]'); clipped=set('$CLIPPED'.split(',')) if '$CLIPPED' else set()
r=[c for c in r if c['slug'] not in clipped]
print(json.dumps(r[0]) if r else '')" "$RANKED" 2>/dev/null)"
    if [ -z "$PICK" ]; then emit "no-eligible-campaign"; exit 0; fi
    SLUG="$("$PY" -c "import json,sys;print(json.loads(sys.argv[1])['slug'])" "$PICK")"
    "$PY" -c "import json,os
p='$STATE'; d=json.load(open(p)) if os.path.exists(p) else {}
pick=json.loads('''$PICK'''); d.update({'phase':'CLIP','campaign_id':pick['slug'],'cpm':pick['cpm'],'budget':pick['budget']})
json.dump(d,open(p,'w'))" 2>/dev/null
    emit "select:$SLUG (cpm=$("$PY" -c "import json,sys;print(json.loads(sys.argv[1])['cpm'])" "$PICK"))"; exit 0
    ;;
  CLIP|POST|SUBMIT|WITHDRAW|STALLED)
    # Wired in subsequent #14 increments (clip via earn-clip-rewards / post via ig-reels-poster to a WARMED
    # account / submit / withdraw), each under run_step. POST is gated on a Day-7-warmed account (REQ-4 +
    # promote.fun's own "warm the account up properly" rule). Until wired, narrate honestly — NO fake success.
    emit "execute:$TRANS:not-yet-wired (#14)"; exit 0
    ;;
  *)
    emit "unknown-transition:$TRANS"; exit 0
    ;;
esac
