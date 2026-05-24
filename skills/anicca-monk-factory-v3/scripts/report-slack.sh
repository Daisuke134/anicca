#!/usr/bin/env bash
# Post a message to Slack #metrics ({{profile.channels.reportChannel}}). MANDATORY at the end of every factory run —
# this is how Dais knows the work actually happened. Usage: report-slack.sh "<message>"
set -uo pipefail
source ~/.openclaw/.env 2>/dev/null || true
: "${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN missing}"
CH="${SLACK_METRICS_CHANNEL:-{{profile.channels.reportChannel}}}"
MSG="$1"
curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" -H "Content-Type: application/json; charset=utf-8" \
  -d "$(jq -n --arg c "$CH" --arg t "$MSG" '{channel:$c,text:$t}')" | jq -r '"ok="+(.ok|tostring)+" ts="+(.ts//"-")+" err="+(.error//"-")'
