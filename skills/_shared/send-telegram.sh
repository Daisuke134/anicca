#!/usr/bin/env bash
# send-telegram.sh — generic Telegram report sender for ANY loop (clip, gig, video, etc).
# The LLM composes the natural-language summary; this tool only does the deterministic send
# (per feedback_build_agents_not_hardcode_regex: model does judgment, tool does the mechanical part).
#
#   bash send-telegram.sh "<message text>" [chat_id]
#
# Uses TELEGRAM_BOT_TOKEN from the Mr.bot state env. The chat id must be passed explicitly or
# configured as TELEGRAM_ALERT_CHAT_ID; OSS source never embeds a user's destination.
set -uo pipefail
MSG="${1:?usage: send-telegram.sh \"<message>\" [chat_id]}"

MR_BOT_STATE_HOME="${MR_BOT_STATE_HOME:-$HOME/.local/state/mr-bot}"
ENV_FILES=()
if [ -n "${MR_BOT_ENV_FILE:-}" ]; then
  ENV_FILES+=("$MR_BOT_ENV_FILE")
else
  ENV_FILES+=("$MR_BOT_STATE_HOME/.env" "$HOME/.openclaw/.env")
fi
for ENV_FILE in "${ENV_FILES[@]}"; do
  if [ -f "$ENV_FILE" ]; then
    set -a; . "$ENV_FILE" 2>/dev/null; set +a
    # The Mr.bot state file may intentionally contain only LM_* names;
    # continue to the OpenClaw compatibility env until the sender token exists.
    [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && break
  fi
done
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"
CHAT_ID="${2:-${TELEGRAM_ALERT_CHAT_ID:?chat_id argument or TELEGRAM_ALERT_CHAT_ID is required}}"

API_HOST="api.telegram.org"
API_URL="https://${API_HOST}/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
RESP=""
CURL_RC=0
RESP=$(curl -sS --max-time 10 "$API_URL" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "disable_web_page_preview=false") || CURL_RC=$?

# Some managed macOS execution contexts have an empty system resolver while
# direct HTTPS remains available. Resolve through a public DNS server only as
# a transport fallback; --resolve preserves the Telegram hostname for TLS.
if [ "$CURL_RC" -ne 0 ] && command -v dig >/dev/null 2>&1; then
  API_IP="$(dig +short +time=2 +tries=1 @1.1.1.1 "$API_HOST" A 2>/dev/null \
    | awk '/^[0-9.]+$/{print; exit}')"
  if [ -n "$API_IP" ]; then
    RESP=$(curl -sS --max-time 10 --resolve "${API_HOST}:443:${API_IP}" "$API_URL" \
      --data-urlencode "chat_id=${CHAT_ID}" \
      --data-urlencode "text=${MSG}" \
      --data-urlencode "disable_web_page_preview=false") || CURL_RC=$?
  fi
fi

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
