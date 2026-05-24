#!/usr/bin/env bash
# Generate 1 HeyGen Avatar IV video per bank entry. Cache forever.
# Output: ~/anicca-monk-factory/state/cached_<entry_id>.mp4 (75sec each, photoreal lip-sync, audio embedded)
# Daily cron then just rotates the cache → $0/render.
# Re-run when bank_en.jsonl gets new entries (winner-analyzer hook).
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
STATE="$ROOT/state"
BANK="$ROOT/scripts/bank_en.jsonl"
set -a; . "$ROOT/.env"; set +a

[ -f "$BANK" ] || { echo "❌ bank not found: $BANK"; exit 1; }

echo "═══════════════════════════════════════════════"
echo "  preload-bank-library.sh — cache HeyGen videos"
echo "  voice path: ${EN_VOICE_PATH:-elevenlabs}"
echo "═══════════════════════════════════════════════"
echo ""

GEN=0; CACHED=0; FAILED=0
while IFS= read -r LN; do
  [ -z "$LN" ] && continue
  EID=$(echo "$LN" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('id',''))" 2>/dev/null)
  TEXT=$(echo "$LN" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('full_text',''))" 2>/dev/null)
  [ -z "$EID" ] && continue

  OUT="$STATE/cached_${EID}.mp4"
  if [ -f "$OUT" ] && [ -s "$OUT" ]; then
    echo "  ✓ $EID cached ($(du -h "$OUT" | cut -f1))"
    CACHED=$((CACHED+1))
    continue
  fi

  echo "  📤 $EID via HeyGen Avatar IV..."

  if [ "${EN_VOICE_PATH:-elevenlabs}" = "elevenlabs" ]; then
    # ElevenLabs TTS → audio_asset_id route
    export TEXT
    TTS_PAYLOAD=$(python3 -c "
import json,os
print(json.dumps({'text':os.environ['TEXT'],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.55,'similarity_boost':0.85,'style':0.15,'speed':0.9,'use_speaker_boost':True}}))")
    NAR="$STATE/cached_${EID}_narration.mp3"
    curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/${EN_VOICE_ID}" \
      -H "xi-api-key: $ELEVENLABS_API_KEY" -H "Content-Type: application/json" \
      -d "$TTS_PAYLOAD" --output "$NAR"
    if [ ! -s "$NAR" ] || [ "$(stat -f %z "$NAR")" -lt 5000 ]; then
      echo "    ❌ ElevenLabs TTS failed for $EID"; FAILED=$((FAILED+1)); continue
    fi
    ASSET_RESP=$(heygen asset create --file "$NAR" 2>&1)
    ASSET_ID=$(echo "$ASSET_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('asset_id',''))" 2>/dev/null)
    if [ -z "$ASSET_ID" ]; then
      echo "    ❌ heygen asset upload failed: $(echo "$ASSET_RESP" | head -c 200)"; FAILED=$((FAILED+1)); continue
    fi
    export ASSET_ID
    HEYGEN_PAYLOAD=$(python3 -c "
import json,os
print(json.dumps({'type':'avatar','avatar_id':os.environ['HEYGEN_EN_AVATAR_LOOK_ID'],'audio_asset_id':os.environ['ASSET_ID'],'aspect_ratio':'9:16'}))")
  else
    # HeyGen built-in voice + script (no ElevenLabs)
    export TEXT
    HEYGEN_PAYLOAD=$(python3 -c "
import json,os
print(json.dumps({'type':'avatar','avatar_id':os.environ['HEYGEN_EN_AVATAR_LOOK_ID'],'script':os.environ['TEXT'],'voice_id':os.environ['HEYGEN_EN_VOICE_ID'],'aspect_ratio':'9:16'}))")
  fi

  RESP=$(heygen video create --wait --timeout 15m -d "$HEYGEN_PAYLOAD" 2>&1)
  URL=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('video_url',''))" 2>/dev/null)
  if [ -z "$URL" ]; then
    echo "    ❌ heygen video create failed: $(echo "$RESP" | head -c 300)"; FAILED=$((FAILED+1)); continue
  fi
  curl -sS -o "$OUT" "$URL"
  if [ ! -s "$OUT" ]; then
    echo "    ❌ download failed for $EID"; FAILED=$((FAILED+1)); continue
  fi
  echo "    ✅ $EID → $OUT ($(du -h "$OUT" | cut -f1))"
  GEN=$((GEN+1))
done < "$BANK"

echo ""
echo "  summary: $CACHED already-cached, $GEN newly-generated, $FAILED failed"
echo "  💰 cost this run: \$$(python3 -c "print(round($GEN*2.85,2))")"
echo "  📊 total cached: $(ls "$STATE"/cached_en-*.mp4 2>/dev/null | wc -l | tr -d ' ') videos"
echo "  → daily yangmun cron now \$0/render"
