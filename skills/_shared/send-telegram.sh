#!/usr/bin/env bash
# send-telegram.sh — generic Telegram report sender for ANY loop (clip, gig, video, etc).
# The LLM composes the natural-language summary; this tool only does the deterministic send
# (per feedback_build_agents_not_hardcode_regex: model does judgment, tool does the mechanical part).
#
#   bash send-telegram.sh "<message text>" [chat_id]
#
# Uses TELEGRAM_BOT_TOKEN from the Life Manager state env. The chat id must be passed explicitly or
# configured as TELEGRAM_ALERT_CHAT_ID; OSS source never embeds a user's destination.
set -uo pipefail
MSG="${1:?usage: send-telegram.sh \"<message>\" [chat_id]}"

LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
set -a; . "${LIFE_MANAGER_ENV_FILE:-$LIFE_MANAGER_STATE_HOME/.env}" 2>/dev/null; set +a
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"
CHAT_ID="${2:-${TELEGRAM_ALERT_CHAT_ID:?chat_id argument or TELEGRAM_ALERT_CHAT_ID is required}}"

RESP=$(curl -sS --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "disable_web_page_preview=false")

OK=$(printf '%s' "$RESP" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("ok", False))
except Exception: print(False)' 2>/dev/null)

if [ "$OK" = "True" ]; then
  echo "TELEGRAM_SENT=true"
  exit 0
else
  echo "TELEGRAM_SENT=false RESP=$RESP"
  exit 1
fi
