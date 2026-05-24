#!/usr/bin/env bash
# ONE-TIME bootstrap: generate 13 Kling i2v animated clips from cached fal flux refs.
# Output: ~/anicca-monk-factory/state/jp_kling_clip_NN.mp4 (5sec each, audio-independent motion)
# After running once, daily cron's generate.sh just `cp` these clips per render = $0/render.
# Re-run only if motion list changes or refs are replaced.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
STATE="$ROOT/state"
set -a; . "$ROOT/.env"; set +a

# 13 motion prompts (locked, isshin/watercolor-monk persona)
declare -a MOTIONS=(
  "seated on wooden veranda, soft breathing motion, cherry petals drifting down"
  "walking along mountain path, cherry petals drifting, gentle wind in robe"
  "seated cross-legged in zen garden, eyes closing slowly, dappled light shifting"
  "standing still by the stream, gentle water reflection movement, calm gaze"
  "walking through flower field, butterflies passing softly"
  "standing on cliff edge, clouds moving slowly across sky behind him"
  "holding paper umbrella in rain, raindrops falling gently around"
  "walking through mossy bamboo forest, dappled sunlight through leaves"
  "seated near hearth with warm flickering fire, soft glow on face"
  "standing on sunset hilltop, warm orange light, robe gently fluttering"
  "walking with paper lantern at dusk along stone path, soft breeze"
  "hands together in gassho prayer, slight forward bow, eyes closed peacefully"
  "looking up at sky with peaceful smile, soft clouds drifting, close-up"
)

echo "═══════════════════════════════════════════════"
echo "  preload-kling-library.sh — 13 cached clips"
echo "  cost: 13 × \$0.21 = \$2.73 (one-time)"
echo "═══════════════════════════════════════════════"
echo ""

# Submit all 13 in parallel
declare -a REQS
for i in 02 03 04 05 06 07 08 09 10 12 13; do
  OUT="$STATE/jp_kling_clip_$i.mp4"
  if [ -f "$OUT" ] && [ -s "$OUT" ]; then
    echo "  ✓ $i cached ($(du -h "$OUT" | cut -f1))"
    REQS[10#$i]=""
    continue
  fi
  IDX=$((10#$i - 1))
  IMG_URL=$(cat "$STATE/jp_url_$i.txt")
  MOTION="${MOTIONS[$IDX]}"
  export IMG_URL MOTION
  KLING_PAYLOAD=$(python3 -c "
import json, os
print(json.dumps({'image_url':os.environ['IMG_URL'],'prompt':os.environ['MOTION'],'duration':'5','aspect_ratio':'9:16'}))")

  echo "  📤 submit $i: ${MOTION:0:60}..."
  RESP=$(curl -sS -X POST "https://queue.fal.run/fal-ai/kling-video/v2.5-turbo/standard/image-to-video" \
    -H "Authorization: Key $FAL_KEY" -H "Content-Type: application/json" -d "$KLING_PAYLOAD")
  REQ=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('request_id',''))")
  if [ -z "$REQ" ]; then
    echo "    ❌ failed to submit: $(echo "$RESP" | head -c 200)"
    continue
  fi
  REQS[10#$i]="$REQ"
done

# Poll all
echo ""
echo "  ⏳ polling fal queue (max 80 × 8s = 10min)..."
for i in 02 03 04 05 06 07 08 09 10 12 13; do
  REQ="${REQS[10#$i]:-}"
  [ -z "$REQ" ] && continue
  OUT="$STATE/jp_kling_clip_$i.mp4"
  for n in $(seq 1 80); do
    STAT=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ/status" -H "Authorization: Key $FAL_KEY" 2>/dev/null \
      | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo '')
    if [ "$STAT" = "COMPLETED" ]; then
      VURL=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ" -H "Authorization: Key $FAL_KEY" \
        | python3 -c "import json,sys; print(json.load(sys.stdin)['video']['url'])")
      curl -sS -o "$OUT" "$VURL"
      echo "  ✅ $i → $OUT ($(du -h "$OUT" | cut -f1))"
      break
    fi
    sleep 8
  done
done

echo ""
echo "  📊 total cached: $(ls "$STATE"/jp_kling_clip_*.mp4 2>/dev/null | wc -l | tr -d ' ')/13"
echo "  💾 total size: $(du -sch "$STATE"/jp_kling_clip_*.mp4 2>/dev/null | tail -1 | cut -f1)"
echo "  → daily watercolor cron now \$0/render"
