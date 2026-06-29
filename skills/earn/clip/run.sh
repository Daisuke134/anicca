#!/usr/bin/env bash
# earn/clip — ONE bounded unit per wake: post the next QUEUED captioned 9:16 clip to the
# next READY clip account (each account lives in its OWN isolated CloakBrowser profile+port,
# so there is never account-switch pollution). Per-view reward USDC accrues LATER, so a post
# records a narrate line (earn_usdc=0); a separate payout-check wake records the real
# on-chain inflow via record-earn (INV-7). NO HUMAN: login uses stored creds + auto-OTP,
# captcha→CapSolver, publish→autonomous. This is a LOCAL slot (needs CloakBrowser on this Mac).
#
# Contract (run-skill.mjs): reads env, does ONE bounded step, prints ONE structured stdout
# line, exits 0. Idempotent + bounded (respects SKILL_TIMEOUT_S). Never posts to the wrong
# account (the poster has a fail-closed account-guard).
#
#   EARN_MODE=discover (default) → report what's postable, no side effect.
#   EARN_MODE=execute            → post ONE queued clip to ONE ready account.
set -uo pipefail

EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-}"
HOME_DIR="${HOME}"
QUEUE="$HOME_DIR/clips/queue"            # *.mp4 + matching *.txt caption, filled by the producer
POSTED="$HOME_DIR/clips/posted"
ACCTS="$HOME_DIR/.cloak/clip-accounts.json"
LEDGER="${EARN_LEDGER:-$HOME_DIR/.openclaw/state/clip-earn-ledger.jsonl}"
POSTER="$HOME_DIR/.claude/skills/ig-reels-poster/scripts/post_reel.py"
CDP_DIR="$HOME_DIR/.claude/skills/ig-account-create/scripts"
PY=/opt/homebrew/bin/python3
mkdir -p "$QUEUE" "$POSTED" "$(dirname "$LEDGER")"

emit() { printf '{"slot":"earn/clip","did":%s,"earned_usdc":0,"cost_usdc":0}\n' "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"; }

# next queued clip (oldest first) that has a caption sidecar
CLIP=""; CAP=""
for f in "$QUEUE"/*.mp4; do
  [ -e "$f" ] || continue
  c="${f%.mp4}.txt"
  if [ -f "$c" ]; then CLIP="$f"; CAP="$c"; break; fi
done

# next ready account (status==ready) + its isolated profile port
read -r HANDLE PORT < <("$PY" - "$ACCTS" <<'PYJSON' 2>/dev/null
import json,sys
try:
    a=json.load(open(sys.argv[1]))
except Exception:
    a=[]
for x in a:
    if x.get("status")=="ready":
        print(x.get("handle",""), x.get("port",9222)); break
PYJSON
)

if [ -z "${CLIP}" ] || [ -z "${HANDLE:-}" ]; then
  emit "nothing to post (queued_clip=${CLIP:-none} ready_account=${HANDLE:-none})"; exit 0
fi

if [ "$EARN_MODE" != "execute" ]; then
  emit "discover: would post $(basename "$CLIP") to @${HANDLE} (port ${PORT})"; exit 0
fi

# --- execute: confirm the account's isolated browser is UP and logged in (no human) ---
TID="$(curl -sS --max-time 5 "http://localhost:${PORT}/json/list" 2>/dev/null | "$PY" -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
ps=[t for t in d if t.get("type")=="page" and "instagram.com" in (t.get("url") or "")]
print((ps[0] if ps else (next((t for t in d if t.get("type")=="page"), {}))).get("id",""))
')"
if [ -z "$TID" ]; then
  emit "account @${HANDLE} browser not up on :${PORT} (warmer/creator must keep it logged in)"; exit 0
fi

# verify logged in as HANDLE (fail-closed: do not post if we cannot confirm)
ACTIVE="$(CDP_PORT="$PORT" "$PY" -c "
import sys,os; sys.path.insert(0,'$CDP_DIR'); import cdp
tid='$TID'
try:
    cdp.navigate(tid,'https://www.instagram.com/'); import time; time.sleep(5)
    print(cdp.evaluate(tid,'(()=>(document.querySelector(\"img[alt\$=のプロフィール写真]\")||{}).alt||\"\")()') or '')
except Exception as e:
    print('')
" 2>/dev/null | sed 's/のプロフィール写真//')"
if [ "$ACTIVE" != "$HANDLE" ]; then
  emit "account @${HANDLE} not logged in on :${PORT} (active='${ACTIVE}') — skipping, no wrong-account post"; exit 0
fi

# post the clip (poster has its own fail-closed account-guard too)
RES="$(CDP_PORT="$PORT" "$PY" "$POSTER" --video "$CLIP" --caption-file "$CAP" --handle "$HANDLE" --tid "$TID" --live 2>/dev/null | tail -1)"
URL="$(printf '%s' "$RES" | "$PY" -c 'import json,sys
try: d=json.loads(sys.stdin.read()); print(d.get("post_url") or "")
except Exception: print("")')"

if [ -n "$URL" ]; then
  mv "$CLIP" "$POSTED/" 2>/dev/null || true
  mv "$CAP"  "$POSTED/" 2>/dev/null || true
  # narrate ledger line (earn_usdc=0; real USDC is recorded by the payout-check wake)
  "$PY" - "$LEDGER" "$HANDLE" "$URL" "$WAKE" <<'PYL' 2>/dev/null
import json,sys,os
ledger,handle,url,wake=sys.argv[1:5]
line={"slot":"earn/clip","source":"ig-clip","task":f"posted reel to @{handle}: {url}",
      "earn_usdc":0,"cost_usdc":0,"net_usdc":0,"wake":wake or None,"post_url":url}
with open(ledger,"a") as f: f.write(json.dumps(line,ensure_ascii=False)+"\n")
PYL
  emit "posted @${HANDLE}: ${URL}"; exit 0
fi
emit "post attempt did not confirm a live URL (res=${RES})"; exit 0
