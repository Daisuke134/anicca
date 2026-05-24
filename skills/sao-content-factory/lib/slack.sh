#!/usr/bin/env bash
# lib/slack.sh — Slack #metrics report wrapper
set -euo pipefail

# slack_metrics <text>
# Posts to #metrics channel. Returns ts on stdout.
slack_metrics() {
  local text="$1"
  [ -z "${SLACK_BOT_TOKEN:-}" ] && { echo "ERR: SLACK_BOT_TOKEN not set" >&2; return 3; }

  local channel_id="${SLACK_METRICS_CHANNEL:-{{profile.channels.reportChannel}}}"

  local response ok ts
  response=$(curl -sS -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$(jq -nc --arg ch "$channel_id" --arg text "$text" \
        '{channel:$ch, text:$text, mrkdwn:true}')")

  ok=$(echo "$response" | jq -r '.ok // false')
  ts=$(echo "$response" | jq -r '.ts // empty')
  if [ "$ok" != "true" ]; then
    echo "ERR: slack post failed: $response" >&2
    return 4
  fi
  printf "%s" "$ts"
}
