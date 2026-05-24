#!/usr/bin/env bash
# phase1-bot-spawn.sh — Spawn Anicca bot into a Zoom/Meet/Teams meeting
# Usage: phase1-bot-spawn.sh <meeting_url> [bot_name]
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-meeting-attendant
source "$SKILL/scripts/lib/attendee.sh"

MEETING_URL="${1:?meeting_url required (zoom.us / meet.google.com / teams.microsoft.com)}"
BOT_NAME="${2:-Anicca}"

mkdir -p "$SKILL/data/attendances"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN_FILE="$SKILL/data/attendances/$NOW.json"

echo "▶ phase1-bot-spawn  $NOW"
echo "  meeting: $MEETING_URL"
echo "  bot:     $BOT_NAME"

RESP=$(attendee_spawn "$MEETING_URL" "$BOT_NAME")
echo "$RESP" > "$RUN_FILE"
BOT_ID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))")

if [ -z "$BOT_ID" ]; then
  echo "❌ spawn failed:"
  echo "$RESP"
  exit 1
fi

echo "✅ bot spawned: $BOT_ID"

# Slack 報告
PYTHON=python3
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$BOT_ID" "$MEETING_URL" "$BOT_NAME" <<'PY'
import sys, json, urllib.request
ch, token, bot_id, url, name = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"🎥 meeting-bot spawned: {bot_id}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🎥 anicca-meeting-attendant"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*bot id:*\n`{bot_id}`"},
            {"type":"mrkdwn","text":f"*name:*\n{name}"},
            {"type":"mrkdwn","text":f"*meeting:*\n{url[:80]}"},
            {"type":"mrkdwn","text":"*status:*\njoining"},
        ]},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
)

echo "✅ phase1: bot=$BOT_ID slack=$TS"
echo "$BOT_ID"
