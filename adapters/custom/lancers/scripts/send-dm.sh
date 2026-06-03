#!/usr/bin/env bash
# adapters/custom/lancers/scripts/send-dm.sh <thread_url> <body>
# Send a DM in an existing Lancers thread using camofox + saved session.
# Enforces ≤ 10 DM/h via state/dm-log.jsonl sleep gate.
#
# Exit:
#   0 = DM sent (or rate-limit sleep-then-sent)
#   2 = bad args / no session
#   3 = CAPTCHA hit
#   4 = rate cap and --no-wait

set -uo pipefail

[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

THREAD_URL="${1:-}"
BODY="${2:-}"

if [ -z "$THREAD_URL" ] || [ -z "$BODY" ]; then
  echo "usage: send-dm.sh <thread_url> <body>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/dm-log.jsonl"
touch "$LOG"
chmod 600 "$LOG"

USER_ID="anicca"
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"

# 1. Rate cap: count sent DMs in last 3600s
NOW=$(date -u +%s)
RECENT=$(awk -v cutoff=$((NOW - 3600)) -F'"ts_unix":' '
  /sent/ {
    ts = $2 + 0
    if (ts >= cutoff) c++
  }
  END { print c+0 }
' "$LOG")

if [ "$RECENT" -ge 10 ]; then
  WAIT=$((3600 / 10))
  echo "[lancers/send-dm] rate cap hit ($RECENT/h). Sleeping ${WAIT}s before retry." >&2
  sleep "$WAIT"
fi

# 2. Health check
if ! curl -sS "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[lancers/send-dm] camofox not alive" >&2
  exit 2
fi

# 3. Open thread URL in saved session
TAB_ID=$(curl -sS -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$THREAD_URL\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')

if [ -z "$TAB_ID" ]; then
  echo "[lancers/send-dm] failed to open tab" >&2
  exit 2
fi
sleep 2

# 4. Snapshot → find textarea + submit button by role/name in text format
SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha'; then
  echo "[lancers/send-dm] CAPTCHA — exit per HARD RULE #-1" >&2
  exit 3
fi

# Camofox text snapshot format: `textbox "label" [eN]` or `textarea ...` rows
TEXTAREA_REF=$(echo "$SNAP" | grep -iE '(textbox|textarea)[^[]*\[e[0-9]+\]' | grep -oE 'e[0-9]+' | head -1)
SUBMIT_REF=$(echo "$SNAP" | grep -iE 'button[^[]*"[^"]*(送信|送る|Send)[^"]*"[^[]*\[e[0-9]+\]' | grep -oE 'e[0-9]+' | head -1)

if [ -z "$TEXTAREA_REF" ] || [ "$TEXTAREA_REF" = "null" ]; then
  echo "[lancers/send-dm] no textarea found on $THREAD_URL — session may be stale" >&2
  exit 2
fi

# 5. Type body
curl -sS -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg ref "$TEXTAREA_REF" --arg text "$BODY" --arg u "$USER_ID" --arg s "$SESSION_KEY" \
    '{ref:$ref, text:$text, userId:$u, sessionKey:$s}')" >/dev/null

# 6. Click submit (if button found) else press Ctrl+Enter
if [ -n "$SUBMIT_REF" ] && [ "$SUBMIT_REF" != "null" ]; then
  curl -sS -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
    -H 'Content-Type: application/json' \
    -d "{\"ref\":\"$SUBMIT_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
fi
sleep 2

# 7. Confirm sent by re-snapshot — look for the body text in the thread
CONFIRM=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
if echo "$CONFIRM" | grep -qF "$(echo "$BODY" | head -c 40)"; then
  STATUS="sent"
else
  STATUS="unconfirmed"
fi

# 8. Append to log
jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg ts_unix "$NOW" \
  --arg url "$THREAD_URL" \
  --arg body "$BODY" \
  --arg status "$STATUS" \
  '{ts:$ts, ts_unix:($ts_unix|tonumber), url:$url, body:$body, status:$status}' \
  >> "$LOG"

echo "[lancers/send-dm] $STATUS — logged to $LOG"
[ "$STATUS" = "sent" ] && exit 0 || exit 2
