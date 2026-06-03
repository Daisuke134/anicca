#!/usr/bin/env bash
# adapters/custom/bland-ai/scripts/outbound-call.sh <phone> <script> [voice] [--dry-run]
# Thin wrapper around POST https://api.bland.ai/v1/calls.
#
# Args:
#   $1 phone   = E.164, e.g. +818012345678
#   $2 script  = the agent's task / first-turn prompt
#   $3 voice   = optional voice id (default "maya")
#   $4 --dry-run = if present, sets should_call=false (Bland echoes config without dialing)
#
# Exit:
#   0 = HTTP 2xx + call_id returned (or dry-run echoed)
#   2 = bad args / API error
#   3 = BLAND_API_KEY missing (= round-2 signup task for Anicca, not human escalation)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

PHONE="${1:-}"
TASK="${2:-}"
VOICE="${3:-maya}"
DRY_RUN_FLAG="${4:-}"

if [ -z "$PHONE" ] || [ -z "$TASK" ]; then
  echo "usage: outbound-call.sh <phone> <script> [voice] [--dry-run]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/call-log.jsonl"
touch "$LOG"
chmod 600 "$LOG"

if [ -z "${BLAND_API_KEY:-}" ]; then
  jq -nc \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg phone "$PHONE" \
    '{ts:$ts, phone:$phone, status:"missing-key", note:"BLAND_API_KEY not provisioned — round-2 signup task"}' \
    >> "$LOG"
  echo "[bland-ai] BLAND_API_KEY missing — recorded uncertainty, exit 3" >&2
  exit 3
fi

# Rate cap: ≤ 20 calls/hour
NOW=$(date -u +%s)
RECENT=$(awk -v cutoff=$((NOW - 3600)) -F'"ts_unix":' '
  /"placed"|"dry-run"/ { ts = $2 + 0; if (ts >= cutoff) c++ }
  END { print c+0 }
' "$LOG")

if [ "$RECENT" -ge 20 ]; then
  WAIT=180
  echo "[bland-ai] rate cap hit ($RECENT/h). Sleeping ${WAIT}s." >&2
  sleep "$WAIT"
fi

# Build payload
if [ "$DRY_RUN_FLAG" = "--dry-run" ]; then
  PAYLOAD=$(jq -nc \
    --arg phone "$PHONE" \
    --arg task "$TASK" \
    --arg voice "$VOICE" \
    '{phone_number:$phone, task:$task, voice:$voice, should_call:false}')
  STATUS_TAG="dry-run"
else
  PAYLOAD=$(jq -nc \
    --arg phone "$PHONE" \
    --arg task "$TASK" \
    --arg voice "$VOICE" \
    '{phone_number:$phone, task:$task, voice:$voice}')
  STATUS_TAG="placed"
fi

RESP=$(curl -sS -X POST "https://api.bland.ai/v1/calls" \
  -H "Authorization: $BLAND_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

CALL_ID=$(echo "$BODY" | jq -r '.call_id // .id // empty' 2>/dev/null)

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg ts_unix "$NOW" \
  --arg phone "$PHONE" \
  --arg status "$STATUS_TAG" \
  --arg http "$HTTP_CODE" \
  --arg call_id "$CALL_ID" \
  --arg body "$BODY" \
  '{ts:$ts, ts_unix:($ts_unix|tonumber), phone:$phone, status:$status, http:($http|tonumber), call_id:$call_id, body:$body}' \
  >> "$LOG"

echo "[bland-ai] http=$HTTP_CODE status=$STATUS_TAG call_id=$CALL_ID"
[ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ] && exit 0 || exit 2
