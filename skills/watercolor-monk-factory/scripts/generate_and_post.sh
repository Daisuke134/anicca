#!/usr/bin/env bash
# Main pipeline: pick script → generate audio → generate avatar video → caption → post.
# Invoked by the cron via the anicca agent.
#
# Usage: generate_and_post.sh <lang: en|jp> <slot: morning|evening> <postiz_integration_id>
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

LANG="${1:?lang required}"
SLOT="${2:?slot required}"
POSTIZ_ID="${3:?postiz integration id required}"

TS=$(date +%Y%m%d_%H%M%S)
ROOT="$HOME/anicca-monk-factory"
CHAR="$ROOT/characters/$LANG"
STATE="$ROOT/state"
RENDERS="$ROOT/renders"
mkdir -p "$RENDERS" "$STATE"

# --- 0. Preflight ---
bash "$HOME/.openclaw/skills/yangmun-monk-factory/scripts/preflight.sh" "$LANG" || exit 3

# --- 1. Load env ---
set -a
[ -f "$ROOT/.env" ] && . "$ROOT/.env"
[ -f "$HOME/.openclaw/.env" ] && . "$HOME/.openclaw/.env"
set +a

AVATAR_ID=$(cat "$CHAR/avatar_id.txt")
VOICE_ID=$(cat "$CHAR/voice_id.txt")

# --- 2. Pick next script from bank ---
BANK="$ROOT/scripts/bank_$LANG.jsonl"
IDX_FILE="$STATE/last_index_$LANG.json"
IDX=$(python3 -c "
import json, os
p = os.environ['IDX_FILE']
try:
  i = json.load(open(p)).get('index', -1)
except:
  i = -1
i += 1
total = sum(1 for _ in open(os.environ['BANK']))
i %= max(total, 1)
print(i)
" 2>/dev/null)

SCRIPT_JSON=$(sed -n "$((IDX + 1))p" "$BANK")
if [ -z "$SCRIPT_JSON" ]; then
  echo "bank empty or index out of range"; exit 4
fi

FULL_TEXT=$(echo "$SCRIPT_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('full_text') or ' '.join(filter(None, [d.get('hook',''), d.get('body',''), d.get('close','')])))")
HASHTAGS=$(echo "$SCRIPT_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(d.get('hashtags',[])))")
TITLE=$(echo "$SCRIPT_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('title',''))")

echo "📜 selected script idx=$IDX"
echo "    hook: $(echo "$FULL_TEXT" | head -c 100)…"

# --- 3. Generate avatar video (HeyGen Avatar IV does lipsync itself from script) ---
echo "🎬 creating avatar video (this takes ~2-6min)..."
VIDEO_JSON=$(heygen video create --wait --timeout 15m -d "$(python3 -c "
import json, sys
print(json.dumps({
  'type': 'avatar',
  'avatar_id': '$AVATAR_ID',
  'voice_id': '$VOICE_ID',
  'script': sys.argv[1],
  'dimension': {'width': 720, 'height': 1280},
  'caption': True
}))
" "$FULL_TEXT")")

VIDEO_URL=$(echo "$VIDEO_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin).get('data', {})
print(d.get('video_url') or d.get('result', {}).get('video_url', ''))
")

if [ -z "$VIDEO_URL" ]; then
  echo "❌ no video_url in response:"
  echo "$VIDEO_JSON" | head -20
  exit 5
fi

RAW="$RENDERS/${TS}_${LANG}_${SLOT}.mp4"
curl -sS -o "$RAW" "$VIDEO_URL"
echo "✅ downloaded: $RAW"

# --- 4. Validate file ---
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW" 2>/dev/null | head -c 5)
echo "    duration: ${DURATION}s"

# --- 5. Upload to Postiz ---
echo "📤 uploading to Postiz..."
UPLOAD=$(curl -sS -X POST "https://api.postiz.com/public/v1/upload" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -F "file=@$RAW;filename=$(basename $RAW);type=video/mp4")

MEDIA_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
MEDIA_PATH=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")

# --- 6. Post to TikTok ---
echo "📢 posting to TikTok (integration=$POSTIZ_ID)..."
POST_RESP=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json, os
print(json.dumps({
  'type': 'now',
  'date': __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
  'shortLink': False,
  'tags': [],
  'posts': [{
    'integration': {'id': '$POSTIZ_ID'},
    'value': [{'content': '$HASHTAGS', 'image': [{'id': '$MEDIA_ID', 'path': '$MEDIA_PATH'}]}],
    'settings': {
      '__type': 'tiktok',
      'title': '$TITLE',
      'privacy_level': 'PUBLIC_TO_EVERYONE',
      'duet': False,
      'stitch': False,
      'comment': True,
      'brand_content_toggle': False,
      'brand_organic_toggle': False,
      'video_made_with_ai': True,
      'content_posting_method': 'DIRECT_POST'
    }
  }]
}))
")")

echo "$POST_RESP" | python3 -m json.tool 2>/dev/null | head -15

# --- 7. Advance state ---
python3 -c "
import json, os
p = '$IDX_FILE'
json.dump({'index': $IDX, 'ts': '$TS', 'lang': '$LANG', 'slot': '$SLOT'}, open(p, 'w'))
"

echo "✅ done — next run will use index $((IDX + 1))"
