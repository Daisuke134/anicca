#!/usr/bin/env bash
# adapters/custom/agentmail/scripts/send.sh <to> <subject> <text> [inbox]
# Thin curl wrapper around POST https://api.agentmail.to/v0/inboxes/<inbox>/messages/send
#
# Exit:
#   0 = HTTP 2xx + message_id captured
#   2 = bad args / API error / missing env

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

TO="${1:-}"
SUBJECT="${2:-}"
TEXT="${3:-}"
INBOX="${4:-${AGENTMAIL_INBOX_ID:-}}"

if [ -z "$TO" ] || [ -z "$SUBJECT" ] || [ -z "$TEXT" ]; then
  echo "usage: send.sh <to> <subject> <text> [inbox]" >&2
  exit 2
fi

if [ -z "${AGENTMAIL_API_KEY:-}" ]; then
  echo "[agentmail/send] AGENTMAIL_API_KEY missing" >&2
  exit 2
fi

if [ -z "$INBOX" ]; then
  echo "[agentmail/send] inbox arg missing and AGENTMAIL_INBOX_ID not in env" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/sent-log.jsonl"
touch "$LOG"
chmod 600 "$LOG"

# Rate cap: ≤ 60/h
NOW=$(date -u +%s)
RECENT=$(awk -v cutoff=$((NOW - 3600)) -F'"ts_unix":' '
  /sent/ { ts = $2 + 0; if (ts >= cutoff) c++ }
  END { print c+0 }
' "$LOG")

if [ "$RECENT" -ge 60 ]; then
  echo "[agentmail/send] rate cap hit ($RECENT/h). Sleeping 60s." >&2
  sleep 60
fi

PAYLOAD=$(jq -nc \
  --arg to "$TO" \
  --arg subj "$SUBJECT" \
  --arg text "$TEXT" \
  '{to:[$to], subject:$subj, text:$text}')

RESP=$(curl -sS -X POST "https://api.agentmail.to/v0/inboxes/$INBOX/messages/send" \
  -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
MSG_ID=$(echo "$BODY" | jq -r '.message_id // .id // empty' 2>/dev/null)

STATUS="sent"
[ "$HTTP_CODE" -ge 300 ] && STATUS="error"

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg ts_unix "$NOW" \
  --arg to "$TO" \
  --arg subj "$SUBJECT" \
  --arg http "$HTTP_CODE" \
  --arg msg_id "$MSG_ID" \
  --arg status "$STATUS" \
  --arg body "$BODY" \
  '{ts:$ts, ts_unix:($ts_unix|tonumber), to:$to, subject:$subj, http:($http|tonumber), message_id:$msg_id, status:$status, body:$body}' \
  >> "$LOG"

echo "[agentmail/send] http=$HTTP_CODE status=$STATUS message_id=$MSG_ID"
[ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ] && exit 0 || exit 2
