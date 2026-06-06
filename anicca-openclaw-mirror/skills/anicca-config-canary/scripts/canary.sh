#!/usr/bin/env bash
# Daily diff openclaw.json vs .last-good; Slack URGENT on drift.
set -u
SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-}"
CHAN="${SLACK_METRICS_CHANNEL:-C091G3PKHL2}"
LIVE="$HOME/.openclaw/openclaw.json"
LAST="$HOME/.openclaw/openclaw.json.last-good"

if [ ! -f "$LAST" ]; then
  cp "$LIVE" "$LAST"
  echo "canary: seeded .last-good"
  exit 0
fi

# Compare normalized JSON of agents.defaults.model only (the key field for routing)
LIVE_MODEL="$(jq -c '.agents.defaults.model' "$LIVE")"
LAST_MODEL="$(jq -c '.agents.defaults.model' "$LAST")"

if [ "$LIVE_MODEL" != "$LAST_MODEL" ]; then
  MSG=":rotating_light: openclaw config drift: agents.defaults.model changed
last-good=$LAST_MODEL
live=$LIVE_MODEL
check for unexpected doctor --fix or manual edit."
  echo "$MSG"
  if [ -n "$SLACK_BOT_TOKEN" ]; then
    PAYLOAD="$(jq -nc --arg c "$CHAN" --arg t "$MSG" '{channel:$c,text:$t}')"
    curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H 'Content-Type: application/json; charset=utf-8' \
      --data "$PAYLOAD" \
      https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
  fi
  exit 1
fi
# rotate last-good (so next-day diff catches new drift, not old)
cp "$LIVE" "$LAST"
echo "canary: no drift"
