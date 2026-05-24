#!/usr/bin/env bash
set -euo pipefail

slack_post() {
  local channel="$1" text="$2" thread_ts="${3:-}"
  : "${SLACK_BOT_TOKEN:?required}"
  local data
  if [ -n "$thread_ts" ]; then
    data=$(jq -nc --arg ch "$channel" --arg t "$text" --arg ts "$thread_ts" '{channel:$ch, text:$t, mrkdwn:true, thread_ts:$ts}')
  else
    data=$(jq -nc --arg ch "$channel" --arg t "$text" '{channel:$ch, text:$t, mrkdwn:true}')
  fi
  curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    --data "$data" | jq -r '.ts // empty'
}
