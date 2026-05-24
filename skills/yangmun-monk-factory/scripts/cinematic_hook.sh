#!/usr/bin/env bash
# Cinematic hook prefix — fal Kling 3s i2v from a locked source PNG (the avatar's still frame).
# Used as a 2-3s scroll-stopper before the HeyGen talking head body (Shalev pattern: Kling/Veo
# for first 2-3s, HeyGen for 90% body).
#
# Usage: cinematic_hook.sh "<motion prompt>" [duration_sec]
#   echoes the path of the produced 3s mp4 on stdout, or empty string + non-zero on failure.
set -euo pipefail
MOTION="${1:?usage: cinematic_hook.sh <motion> [duration]}"
DURATION="${2:-3}"
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

WORK="$ROOT/renders/hook_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK"

# Use the locked avatar still frame (or a fallback portrait) as Kling source
SRC_IMG="$ROOT/characters/yangmun_monk.png"
if [ ! -f "$SRC_IMG" ]; then
  # Fallback: use one of the existing fal flux refs
  SRC_IMG="$ROOT/state/jp_ref_07.png"
fi

# Upload PNG to fal (or use a locked URL if cached)
CACHED_URL="$ROOT/state/yangmun_monk_url.txt"
if [ -f "$CACHED_URL" ]; then
  IMG_URL=$(cat "$CACHED_URL")
else
  # Inline upload via fal storage (or use a public image hosting)
  RESP=$(curl -sS -X POST "https://queue.fal.run/fal-ai/storage/upload" \
    -H "Authorization: Key $FAL_KEY" \
    -F "file=@$SRC_IMG")
  IMG_URL=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('url',''))" 2>/dev/null || echo '')
  [ -n "$IMG_URL" ] && echo "$IMG_URL" > "$CACHED_URL"
fi

if [ -z "$IMG_URL" ]; then
  echo "❌ no image URL for cinematic hook" >&2
  exit 1
fi

PAYLOAD=$(MOTION="$MOTION" IMG_URL="$IMG_URL" DURATION="$DURATION" python3 -c "
import json, os
print(json.dumps({
  'image_url': os.environ['IMG_URL'],
  'prompt': os.environ['MOTION'],
  'duration': os.environ['DURATION'],
  'aspect_ratio': '9:16'
}))")

RESP=$(curl -sS -X POST "https://queue.fal.run/fal-ai/kling-video/v2.5-turbo/standard/image-to-video" \
  -H "Authorization: Key $FAL_KEY" -H "Content-Type: application/json" \
  -d "$PAYLOAD")
REQ=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('request_id',''))")
[ -z "$REQ" ] && { echo "❌ no fal request_id: $RESP" >&2; exit 2; }

# Poll up to ~7 min
for n in $(seq 1 80); do
  STAT=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ/status" \
    -H "Authorization: Key $FAL_KEY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo '')
  if [ "$STAT" = "COMPLETED" ]; then
    VURL=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ" \
      -H "Authorization: Key $FAL_KEY" | python3 -c "import json,sys; print(json.load(sys.stdin)['video']['url'])")
    OUT="$WORK/hook.mp4"
    curl -sS -o "$OUT" "$VURL"
    echo "$OUT"
    exit 0
  fi
  sleep 6
done

echo "❌ cinematic hook timed out" >&2
exit 3
