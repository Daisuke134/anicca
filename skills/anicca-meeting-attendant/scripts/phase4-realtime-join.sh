#!/usr/bin/env bash
# phase4-realtime-join.sh — Spawn attendee bot with ElevenLabs realtime voice agent
# Usage: phase4-realtime-join.sh <meeting_url> [bot_name] [agent_id]
# Default agent_id = Anicca Realtime
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-meeting-attendant
source "$SKILL/scripts/lib/attendee.sh"

MEETING_URL="${1:?meeting_url required (zoom.us / meet.google.com / teams.microsoft.com)}"
BOT_NAME="${2:-Anicca Realtime}"
AGENT_ID="${3:-agent_6601kr8fjyj3e4hrdb00kv1942ne}"
VOICE_AGENT_URL="${VOICE_AGENT_URL:-https://aniccaai.com/voice-agent/?agent_id=${AGENT_ID}}"

mkdir -p "$SKILL/data/attendances"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN_FILE="$SKILL/data/attendances/realtime-$NOW.json"

echo "▶ phase4-realtime-join  $NOW"
echo "  meeting:    $MEETING_URL"
echo "  bot:        $BOT_NAME"
echo "  agent_id:   $AGENT_ID"
echo "  voice url:  $VOICE_AGENT_URL"

PAYLOAD=$(MEETING_URL="$MEETING_URL" BOT_NAME="$BOT_NAME" VOICE_URL="$VOICE_AGENT_URL" python3 -c '
import json, os
print(json.dumps({
  "meeting_url": os.environ["MEETING_URL"],
  "bot_name":    os.environ["BOT_NAME"],
  "voice_agent_settings": {"url": os.environ["VOICE_URL"]},
}))')

RESP=$(curl -sS -X POST "${ATTENDEE_BASE:-https://app.attendee.dev}/api/v1/bots" \
  -H "Authorization: Token $ATTENDEE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESP" > "$RUN_FILE"
BOT_ID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))")

if [ -z "$BOT_ID" ]; then
  echo "❌ spawn failed:"
  echo "$RESP"
  exit 1
fi

echo "✅ realtime bot spawned: $BOT_ID"

PYTHON=python3
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$BOT_ID" "$MEETING_URL" "$BOT_NAME" "$AGENT_ID" <<'PY'
import sys, json, urllib.request
ch, token, bot_id, url, name, agent_id = sys.argv[1:7]
payload = {
    "channel": ch,
    "text": f"🎙️ realtime meeting bot spawned: {bot_id}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🎙️ anicca-meeting-attendant — realtime"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*bot id:*\n`{bot_id}`"},
            {"type":"mrkdwn","text":f"*agent:*\n`{agent_id}`"},
            {"type":"mrkdwn","text":f"*name:*\n{name}"},
            {"type":"mrkdwn","text":f"*meeting:*\n{url[:80]}"},
            {"type":"mrkdwn","text":"*mode:*\nElevenLabs realtime via voice_agent_settings"},
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

echo "✅ phase4: bot=$BOT_ID slack=$TS"
echo "$BOT_ID"
