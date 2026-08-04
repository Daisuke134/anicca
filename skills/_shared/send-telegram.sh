#!/usr/bin/env bash
# send-telegram.sh — generic Telegram report sender for ANY loop (clip, gig, video, etc).
# The LLM composes the natural-language summary; this tool only does the deterministic send
# (per feedback_build_agents_not_hardcode_regex: model does judgment, tool does the mechanical part).
#
#   bash send-telegram.sh "<message text>" [chat_id]
#
# Backward-compatible wrapper around telegram.py. Configuration comes from the process
# environment or ~/anicca/.env; there is no OpenClaw runtime or secret-path dependency.
set -uo pipefail
MSG="${1:?usage: send-telegram.sh \"<message>\" [chat_id]}"
CHAT_ID="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARGS=("$SCRIPT_DIR/telegram.py")
if [ -n "$CHAT_ID" ]; then
  ARGS+=("--chat-id" "$CHAT_ID")
fi
ARGS+=("text" "$MSG")
RESP=$(python3 "${ARGS[@]}" 2>&1)
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  # MSGID (2026-07-25 addition, backward-compatible): the real Telegram message_id, so a caller
  # that needs to prove a send actually happened (not just TELEGRAM_SENT=true) can cite it. Old
  # callers that only check for the "TELEGRAM_SENT=true" substring are unaffected.
  MSGID=$(printf '%s' "$RESP" | python3 -c 'import json,sys
try: print((json.load(sys.stdin).get("message_ids") or [""])[0])
except Exception: print("")' 2>/dev/null)
  echo "TELEGRAM_SENT=true MSGID=$MSGID"
  exit 0
else
  echo "TELEGRAM_SENT=false RESP=$RESP"
  exit 1
fi
