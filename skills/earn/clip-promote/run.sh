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
mkdir -p "$(dirname "$STATE")" "$(dirname "$LEDGER")" 2>/dev/null || true

# ── portable timeout (FIND-302): GNU `timeout` or coreutils `gtimeout`; else a pure node fallback. ──
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"
run_step() { # run_step <deadline_s> <cmd...> ; returns 124 on timeout
  local d="$1"; shift
  if [ -n "$TIMEOUT_BIN" ]; then
    "$TIMEOUT_BIN" "$d" "$@"; return $?
  fi
  # pure fallback: child killed via SIGTERM after the deadline (exit 124 to mirror coreutils).
  ( "$@" ) & local pid=$!
  ( sleep "$d"; kill -TERM "$pid" 2>/dev/null; sleep 2; kill -KILL "$pid" 2>/dev/null ) & local wd=$!
  if wait "$pid" 2>/dev/null; then kill -TERM "$wd" 2>/dev/null; return 0; fi
  local rc=$?; kill -TERM "$wd" 2>/dev/null
  [ "$rc" -ge 128 ] && return 124 || return "$rc"
}

emit() { # emit <did> [earned_usdc] [cost_usdc]
  "$PY" - "$1" "${2:-0}" "${3:-0}" <<'PYE'
import json,sys
print(json.dumps({"slot":"earn/clip-promote","did":sys.argv[1],
                  "earned_usdc":float(sys.argv[2]),"cost_usdc":float(sys.argv[3])}))
PYE
}

# guard a step's exit code: 124 ⇒ blocked:human (no hang, no human wait), other non-zero ⇒ narrate.
blocked_or() { # blocked_or <step-name> <rc> <narrate-msg-on-nonzero>
  local step="$1" rc="$2" msg="$3"
  if [ "$rc" -eq 124 ]; then emit "blocked:human:$step"; exit 0; fi
  if [ "$rc" -ne 0 ]; then emit "$msg"; exit 0; fi
}

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
  SELECT|CLIP|POST|SUBMIT|WITHDRAW|STALLED)
    # Live transition handlers are wired in #14 (campaign select / clip / post / submit / withdraw against
    # promote.fun + ig-reels-poster + earn-clip-rewards, each via run_step). Until wired, narrate honestly
    # (NO fake success): report the transition without claiming a side effect.
    emit "execute:$TRANS:not-yet-wired (#14)"; exit 0
    ;;
  *)
    emit "unknown-transition:$TRANS"; exit 0
    ;;
esac
