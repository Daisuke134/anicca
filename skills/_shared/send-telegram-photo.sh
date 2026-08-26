#!/usr/bin/env bash
set -euo pipefail

PHOTO_PATH="${1:?usage: send-telegram-photo.sh <photo-path> <caption> [chat_id]}"
CAPTION="${2:?caption is required}"
[ -f "$PHOTO_PATH" ] || { echo "TELEGRAM_PHOTO_SENT=false ERROR=photo_missing"; exit 1; }

LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
ENV_FILES=()
if [ -n "${LIFE_MANAGER_ENV_FILE:-}" ]; then
  ENV_FILES+=("$LIFE_MANAGER_ENV_FILE")
else
  ENV_FILES+=("$LIFE_MANAGER_STATE_HOME/.env" "$HOME/.openclaw/.env")
fi
for ENV_FILE in "${ENV_FILES[@]}"; do
  if [ -f "$ENV_FILE" ]; then
    set -a; . "$ENV_FILE" 2>/dev/null; set +a
    [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && break
  fi
done
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"
CHAT_ID="${3:-${TELEGRAM_ALERT_CHAT_ID:?chat_id argument or TELEGRAM_ALERT_CHAT_ID is required}}"

API_HOST="api.telegram.org"
API_URL="https://${API_HOST}/bot${TELEGRAM_BOT_TOKEN}/sendPhoto"
send_photo() {
  curl -sS --max-time 30 "$@" "$API_URL" \
    -F "chat_id=${CHAT_ID}" \
    -F "caption=${CAPTION}" \
    -F "photo=@${PHOTO_PATH};type=image/png"
}

CURL_RC=0
RESP="$(send_photo)" || CURL_RC=$?
if [ "$CURL_RC" -ne 0 ] && command -v dig >/dev/null 2>&1; then
  API_IP="$(dig +short +time=2 +tries=1 @1.1.1.1 "$API_HOST" A 2>/dev/null | awk '/^[0-9.]+$/{print; exit}')"
  if [ -n "$API_IP" ]; then
    RESP="$(send_photo --resolve "${API_HOST}:443:${API_IP}")" || CURL_RC=$?
  fi
fi

MESSAGE_ID="$(printf '%s' "$RESP" | python3 -c 'import json,sys
try:
    data=json.load(sys.stdin)
    print(data.get("result",{}).get("message_id","") if data.get("ok") else "")
except Exception:
    print("")')"
if [ "$CURL_RC" -eq 0 ] && [ -n "$MESSAGE_ID" ]; then
  printf 'TELEGRAM_PHOTO_SENT=true MSGID=%s\n' "$MESSAGE_ID"
else
  echo "TELEGRAM_PHOTO_SENT=false"
  exit 1
fi
