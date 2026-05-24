#!/usr/bin/env bash
# phase3-end-summary.sh — Pull transcript after meeting + Slack summary
# Usage: phase3-end-summary.sh <bot_id>
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-meeting-attendant
source "$SKILL/scripts/lib/attendee.sh"

BOT_ID="${1:?bot_id required}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
OUT="$SKILL/data/attendances/$BOT_ID-transcript-$NOW.json"

echo "▶ phase3  bot=$BOT_ID"

attendee_transcript "$BOT_ID" > "$OUT"
LINES=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(len(d.get('utterances',d.get('results',[]))))" "$OUT" 2>/dev/null || echo "?")

echo "  transcript: $LINES utterances"
echo "  saved:      $OUT"

# Slack 報告
PYTHON=python3
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$BOT_ID" "$LINES" "$OUT" <<'PY'
import sys, json, urllib.request
ch, token, bot_id, lines, path = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"🎥 meeting-bot summary: {bot_id} ({lines} utterances)",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🎥 meeting summary"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*bot id:*\n`{bot_id}`"},
            {"type":"mrkdwn","text":f"*utterances:*\n{lines}"},
        ]},
        {"type":"context","elements":[{"type":"mrkdwn","text":f"transcript: `{path}`"}]},
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

echo "✅ phase3: utterances=$LINES slack=$TS"
