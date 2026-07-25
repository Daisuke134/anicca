#!/usr/bin/env bash
# send-telegram.sh — generic Telegram report sender for ANY loop (clip, gig, video, etc).
# The LLM composes the natural-language summary; this tool only does the deterministic send
# (per feedback_build_agents_not_hardcode_regex: model does judgment, tool does the mechanical part).
#
#   bash send-telegram.sh "<message text>" [chat_id]
#
# Uses TELEGRAM_BOT_TOKEN from ~/.openclaw/.env. Default chat_id = Dais's chat (8547730585),
# the same one OpenClaw's own crons already report to.
set -uo pipefail
MSG="${1:?usage: send-telegram.sh \"<message>\" [chat_id]}"
CHAT_ID="${2:-8547730585}"

set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set in ~/.openclaw/.env}"

RESP=$(curl -sS --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "disable_web_page_preview=false")

OK=$(printf '%s' "$RESP" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("ok", False))
except Exception: print(False)' 2>/dev/null)

if [ "$OK" = "True" ]; then
  # MSGID (2026-07-25 addition, backward-compatible): the real Telegram message_id, so a caller
  # that needs to prove a send actually happened (not just TELEGRAM_SENT=true) can cite it. Old
  # callers that only check for the "TELEGRAM_SENT=true" substring are unaffected.
  MSGID=$(printf '%s' "$RESP" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("result",{}).get("message_id",""))
except Exception: print("")' 2>/dev/null)
  echo "TELEGRAM_SENT=true MSGID=$MSGID"
  exit 0
else
  echo "TELEGRAM_SENT=false RESP=$RESP"
  exit 1
fi
