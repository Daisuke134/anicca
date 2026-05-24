#!/usr/bin/env bash
# Upload mp4 to Postiz, fan-out to TikTok + Instagram Reels + YouTube Shorts
# in a SINGLE API call by including all available integrations in posts[].
#
# Usage:  post.sh <en|jp> <final_mp4_path> [legacy_postiz_id_ignored]
# Reads integration IDs from env (.env):
#   POSTIZ_<LANG>_TIKTOK_INTEGRATION   (required)
#   POSTIZ_<LANG>_IG_INTEGRATION       (optional)
#   POSTIZ_<LANG>_YT_INTEGRATION       (optional)
# Honors $WARMUP_MODE (true → UPLOAD draft, anything else → DIRECT_POST).
set -euo pipefail
LANG_ARG="${1:?usage: post.sh <en|jp> <mp4>}"
MP4="${2:?}"
# 3rd arg ignored — kept for backward compat with cron messages
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

# Per-language: 100% copy of yangmun2 / isshin caption pattern.
# EN  = short body line + 4 hashtags (yangmun2 pattern, NO USA tag)
# JP  = isshin's 280-400 char structured caption, ZERO hashtags
case "$LANG_ARG" in
  en)
    LANG_UPPER='EN'
    EN_CAPTION_FALLBACKS='[
      "Check the link in my bio for my book 🙏 #buddhism #wellness #wellnesstips #monk",
      "Free monk’s ebook in my bio 🙏 #buddhism #wellness #monk #wisdom",
      "Read my book on impermanence in bio 🙏 #buddhism #wisdom #wellnesstips #zen"
    ]'
    ;;
  jp)
    LANG_UPPER='JP'
    ;;
  *) echo "❌ unknown lang: $LANG_ARG"; exit 2 ;;
esac

# Resolve integration IDs from env by language
TT_VAR="POSTIZ_${LANG_UPPER}_TIKTOK_INTEGRATION"
IG_VAR="POSTIZ_${LANG_UPPER}_IG_INTEGRATION"
YT_VAR="POSTIZ_${LANG_UPPER}_YT_INTEGRATION"
TT_ID="${!TT_VAR:-}"
IG_ID="${!IG_VAR:-}"
YT_ID="${!YT_VAR:-}"
FB_VAR="POSTIZ_${LANG_UPPER}_FB_INTEGRATION"
FB_ID="${!FB_VAR:-}"

if [ -z "$TT_ID" ]; then
  echo "❌ $TT_VAR not set in .env — cannot post" >&2
  exit 3
fi

# Title via Python (safe quoting for emoji / JP)
export LANG_ARG
TITLE=$(python3 - <<'PY'
import json, os
d = json.load(open(os.path.expanduser(f"~/anicca-monk-factory/state/current_{os.environ['LANG_ARG']}.json"), encoding='utf-8'))
print(d.get('title','')[:140], end='')
PY
)

# Caption: read from bank entry's `captions[]` (preferred), else fall back to per-lang default
export EN_CAPTION_FALLBACKS LANG_ARG
CAPTION=$(python3 - <<'PY'
import json, os, random, sys
lang = os.environ['LANG_ARG']
d = json.load(open(os.path.expanduser(f"~/anicca-monk-factory/state/current_{lang}.json"), encoding='utf-8'))
# JP: bank entry's `caption` field (single isshin-style 280-400 char caption)
if lang == 'jp':
    cap = d.get('caption') or d.get('full_text','')[:300]
    print(cap, end='')
else:
    # EN: bank entry's `captions[]` array (3 candidates) — pick random
    caps = d.get('captions') or json.loads(os.environ.get('EN_CAPTION_FALLBACKS','["Check the link in my bio 🙏 #buddhism #wellness #monk #wisdom"]'))
    print(random.choice(caps), end='')
PY
)

WARMUP="${WARMUP_MODE:-true}"
if [ "$WARMUP" = "true" ]; then
  POST_METHOD="UPLOAD"
else
  POST_METHOD="DIRECT_POST"
fi

# Decide which platforms are active
PLATFORMS="tiktok"
[ -n "$IG_ID" ] && PLATFORMS="$PLATFORMS+ig"
[ -n "$YT_ID" ] && PLATFORMS="$PLATFORMS+yt"
[ -n "$FB_ID" ] && PLATFORMS="$PLATFORMS+fb"
echo "📤 Postiz fan-out (lang=$LANG_ARG warmup=$WARMUP method=$POST_METHOD platforms=$PLATFORMS)..." >&2

# 1) Upload MP4 once
UP=$(curl -sS -X POST "https://api.postiz.com/public/v1/upload" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -F "file=@$MP4;filename=$(basename $MP4);type=video/mp4")
MEDIA_ID=$(echo "$UP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
MEDIA_PATH=$(echo "$UP" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
echo "   uploaded: $MEDIA_ID" >&2

# 2) Build multi-integration payload via Python
export MEDIA_ID MEDIA_PATH TT_ID IG_ID YT_ID FB_ID CAPTION TITLE POST_METHOD
PAYLOAD=$(python3 - <<'PY'
import json, os, datetime
posts = []

# TikTok (required)
posts.append({
    'integration': {'id': os.environ['TT_ID']},
    'value': [{
        'content': os.environ['CAPTION'],
        'image': [{'id': os.environ['MEDIA_ID'], 'path': os.environ['MEDIA_PATH']}]
    }],
    'settings': {
        '__type': 'tiktok',
        'title': os.environ['TITLE'],
        'privacy_level': 'PUBLIC_TO_EVERYONE',
        'duet': False,
        'stitch': False,
        'comment': True,
        'brand_content_toggle': False,
        'brand_organic_toggle': False,
        'video_made_with_ai': True,
        'autoAddMusic': 'no',
        'content_posting_method': os.environ['POST_METHOD']
    }
})

# Instagram (vertical video → automatic Reel). post_type must be "post" or "story" per Postiz API.
if os.environ.get('IG_ID'):
    posts.append({
        'integration': {'id': os.environ['IG_ID']},
        'value': [{
            'content': os.environ['CAPTION'],
            'image': [{'id': os.environ['MEDIA_ID'], 'path': os.environ['MEDIA_PATH']}]
        }],
        'settings': {
            '__type': 'instagram',
            'post_type': 'post',
            'video_made_with_ai': True
        }
    })

# YouTube Shorts (optional)
if os.environ.get('YT_ID'):
    posts.append({
        'integration': {'id': os.environ['YT_ID']},
        'value': [{
            'content': os.environ['CAPTION'],
            'image': [{'id': os.environ['MEDIA_ID'], 'path': os.environ['MEDIA_PATH']}]
        }],
        'settings': {
            '__type': 'youtube',
            'title': os.environ['TITLE'],
            'type': 'short',
            'privacy': 'public',
            'made_for_kids': False,
            'video_made_with_ai': True
        }
    })

# Facebook Reels (optional, 4th platform per Shalev)
if os.environ.get('FB_ID'):
    posts.append({
        'integration': {'id': os.environ['FB_ID']},
        'value': [{
            'content': os.environ['CAPTION'],
            'image': [{'id': os.environ['MEDIA_ID'], 'path': os.environ['MEDIA_PATH']}]
        }],
        'settings': {
            '__type': 'facebook',
            'post_type': 'reels',
            'video_made_with_ai': True
        }
    })

print(json.dumps({
    'type': 'now',
    'date': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
    'shortLink': False,
    'tags': [],
    'posts': posts
}))
PY
)

RESP=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESP" | python3 -m json.tool 2>/dev/null | head -20

export RESP
python3 - <<'PY' >> "$ROOT/state/posted.jsonl"
import json, os, datetime
resp_raw = os.environ['RESP']
try:
    resp = json.loads(resp_raw)
except Exception:
    resp = {"raw": resp_raw}
print(json.dumps({
    "ts": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
    "lang": os.environ['LANG_ARG'],
    "tt_id": os.environ.get('TT_ID', ''),
    "ig_id": os.environ.get('IG_ID', ''),
    "yt_id": os.environ.get('YT_ID', ''),
    "method": os.environ['POST_METHOD'],
    "warmup_mode": os.environ.get('WARMUP_MODE', ''),
    "title": os.environ.get('TITLE', ''),
    "response": resp,
}, ensure_ascii=False))
PY
echo "✅ posted ($LANG_ARG → $PLATFORMS)" >&2
