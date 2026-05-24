#!/usr/bin/env bash
# Stage 4: PROOF — generate ONE clone video for Dais visual review.
# Iterates: agent updates clone_spec.json, re-runs Stage 4 with incremented counter.
# Max 5 iterations. After Dais 👍 → Stage 5 spawn.
#
# Production stack routing:
#   fal-flux+ffmpeg-still  → static AI image + voice + BGM + subtitles (Watermelon archetype)
#   fal-flux+kling-i2v     → image-to-video (watercolor archetype)
#   heygen-avatar-iv       → talking-head (yangmun archetype)
set -euo pipefail
RUN_DIR="${1:?run_dir required}"
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

CLONE_SPEC="$RUN_DIR/clone_spec.json"
[ -f "$CLONE_SPEC" ] || { echo "❌ no clone_spec.json — agent must write it first"; exit 2; }

# Honor agent skip
SKIP=$(python3 -c "import json; print('1' if json.load(open('$CLONE_SPEC')).get('skip') else '0')")
[ "$SKIP" = "1" ] && { echo "  ⏭ skip per clone_spec"; exit 0; }

# Iteration counter (max 5)
ITER_FILE="$RUN_DIR/iteration.txt"
[ -f "$ITER_FILE" ] || echo 0 > "$ITER_FILE"
ITER=$(cat "$ITER_FILE")
ITER=$((ITER + 1))
if [ "$ITER" -gt 5 ]; then
  echo "  ⛔ MAX 5 iterations reached — Dais must approve current state OR restart run"
  exit 5
fi
echo $ITER > "$ITER_FILE"

echo ""
echo "─── Stage 4: PROOF iteration $ITER / 5 ───"

PROD=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('production_stack',''))")
FORMAT=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('format_type',''))")
echo "  format=$FORMAT  stack=$PROD"

PICKED="$RUN_DIR/picked.json"
SOURCE_ID=$(python3 -c "import json; print(json.load(open('$PICKED'))['id'])")
SOURCE_MP4="$RUN_DIR/source_${SOURCE_ID}.mp4"
TRANSCRIPT_JSON="$RUN_DIR/source_${SOURCE_ID}.transcript.json"
[ -f "$SOURCE_MP4" ] || { echo "❌ no source mp4 at $SOURCE_MP4"; exit 3; }

# ─── Source aspect detection (always set, used by both fal flux + ffmpeg) ──
SRC_W=$(ffprobe -v 0 -of csv=p=0 -show_entries stream=width -select_streams v:0 "$SOURCE_MP4")
SRC_H=$(ffprobe -v 0 -of csv=p=0 -show_entries stream=height -select_streams v:0 "$SOURCE_MP4")
if [ "$SRC_W" -gt "$SRC_H" ]; then
  FAL_SIZE="landscape_16_9"
elif [ "$SRC_H" -gt "$SRC_W" ]; then
  FAL_SIZE="portrait_16_9"
else
  FAL_SIZE="square_hd"
fi
echo "  📐 source ${SRC_W}x${SRC_H} → fal_size=$FAL_SIZE"

# ─── Provision avatar (fal flux) — cached unless prompt changed ─────
AVATAR_PNG="$RUN_DIR/avatar.png"
PREV_PROMPT_FILE="$RUN_DIR/avatar_prompt.txt"
PROMPT=$(python3 -c "import json; d=json.load(open('$CLONE_SPEC')); print(d.get('avatar',{}).get('fal_flux_prompt',''))")

NEED_AVATAR=1
if [ -f "$AVATAR_PNG" ] && [ -f "$PREV_PROMPT_FILE" ]; then
  if [ "$(cat "$PREV_PROMPT_FILE")" = "$PROMPT" ]; then
    NEED_AVATAR=0
    echo "  📸 avatar cached (prompt unchanged)"
  fi
fi
if [ "$NEED_AVATAR" = "1" ]; then
  echo "  📸 fal flux: generating avatar"
  PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1], 'image_size': sys.argv[2], 'num_images': 1, 'output_format': 'jpeg'}))" "$PROMPT" "$FAL_SIZE")
  RESP=$(curl -sS -X POST "https://fal.run/fal-ai/flux-pro/v1.1" \
    -H "Authorization: Key $FAL_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
  IMG_URL=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('images',[{}])[0].get('url',''))" 2>/dev/null)
  if [ -z "$IMG_URL" ]; then
    echo "  ❌ fal flux error: $(echo "$RESP" | head -c 400)"
    exit 1
  fi
  curl -sS -L "$IMG_URL" -o "$AVATAR_PNG"
  echo "  ✅ avatar.png saved ($(du -h "$AVATAR_PNG" | cut -f1))"
  echo "$PROMPT" > "$PREV_PROMPT_FILE"
fi

# ─── Provision voice (ElevenLabs voice design) — cached ────────────
VOICE_ID_FILE="$RUN_DIR/voice_id.txt"
PREV_VOICE_FILE="$RUN_DIR/voice_desc.txt"
VOICE_DESC=$(python3 -c "import json; d=json.load(open('$CLONE_SPEC')); print(d.get('voice',{}).get('elevenlabs_voice_description',''))")

NEED_VOICE=1
if [ -s "$VOICE_ID_FILE" ] && [ -f "$PREV_VOICE_FILE" ]; then
  if [ "$(cat "$PREV_VOICE_FILE")" = "$VOICE_DESC" ]; then
    NEED_VOICE=0
    echo "  🎙 voice cached (desc unchanged): $(cat "$VOICE_ID_FILE")"
  fi
fi
if [ "$NEED_VOICE" = "1" ]; then
  echo "  🎙 ElevenLabs voice design (curl)"
  SAMPLE="Anicca means impermanence. The breath you held a moment ago is already gone. The grief, the joy, the storm in your chest — they all pass. Sit with this moment, my friend. Let it be enough."
  PREVIEW_PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'voice_description': sys.argv[1], 'text': sys.argv[2]}))" "$VOICE_DESC" "$SAMPLE")
  PREVIEW_RESP=$(curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-voice/create-previews" \
    -H "Content-Type: application/json" -H "xi-api-key: $ELEVENLABS_API_KEY" \
    -d "$PREVIEW_PAYLOAD")
  PREVIEW_ID=$(echo "$PREVIEW_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('previews',[{}])[0].get('generated_voice_id',''))" 2>/dev/null)
  if [ -z "$PREVIEW_ID" ]; then
    echo "  ❌ preview empty: $(echo "$PREVIEW_RESP" | head -c 300)"; exit 1
  fi
  echo "  preview_id: $PREVIEW_ID"
  PERSIST_PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'voice_name': f'cvff_proof_iter{sys.argv[3]}', 'voice_description': sys.argv[1], 'generated_voice_id': sys.argv[2]}))" "$VOICE_DESC" "$PREVIEW_ID" "$ITER")
  PERSIST_RESP=$(curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-voice/create-voice-from-preview" \
    -H "Content-Type: application/json" -H "xi-api-key: $ELEVENLABS_API_KEY" \
    -d "$PERSIST_PAYLOAD")
  VOICE_ID=$(echo "$PERSIST_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('voice_id',''))" 2>/dev/null)
  if [ -z "$VOICE_ID" ]; then
    echo "  ❌ persist empty: $(echo "$PERSIST_RESP" | head -c 300)"; exit 1
  fi
  echo "$VOICE_ID" > "$VOICE_ID_FILE"
  echo "$VOICE_DESC" > "$PREV_VOICE_FILE"
  echo "  ✅ voice_id: $VOICE_ID"
fi
VOICE_ID=$(cat "$VOICE_ID_FILE")

# ─── Extract BGM from source mp4 ────────────────────────────────────
BGM_MP3="$RUN_DIR/bgm.mp3"
if [ ! -f "$BGM_MP3" ]; then
  echo "  🎵 extracting source audio as BGM (will be mixed at low volume under narration)"
  ffmpeg -y -i "$SOURCE_MP4" -vn -acodec libmp3lame -ab 128k "$BGM_MP3" 2>/dev/null
  echo "  ✅ bgm.mp3 ($(du -h "$BGM_MP3" | cut -f1))"
fi

# ─── Build proof script ─────────────────────────────────────────────
# Use source transcript as the proof narration (closest to source delivery).
SCRIPT_TEXT=$(python3 -c "
import json
t = json.load(open('$TRANSCRIPT_JSON'))
print(t.get('text','').strip()[:1200])
")
SCRIPT_LEN=${#SCRIPT_TEXT}
echo "  📝 proof script: $SCRIPT_LEN chars"

# ─── ElevenLabs TTS narration (curl) ───────────────────────────────
NARRATION_MP3="$RUN_DIR/narration_iter${ITER}.mp3"
echo "  🎙 ElevenLabs TTS (curl)"
TTS_PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'text': sys.argv[1], 'model_id': 'eleven_multilingual_v2', 'voice_settings': {'stability': 0.5, 'similarity_boost': 0.85, 'style': 0.15, 'speed': 0.95}}))" "$SCRIPT_TEXT")
HTTP_CODE=$(curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID" \
  -H "Content-Type: application/json" -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Accept: audio/mpeg" \
  -d "$TTS_PAYLOAD" \
  -w "%{http_code}" -o "$NARRATION_MP3")
if [ "$HTTP_CODE" != "200" ]; then
  echo "  ❌ TTS HTTP $HTTP_CODE: $(head -c 200 "$NARRATION_MP3")"
  exit 1
fi
echo "  ✅ narration ($(du -h "$NARRATION_MP3" | cut -f1))"

# ─── Compose video (route by production_stack) ──────────────────────
CLONE_MP4="$RUN_DIR/clone_iter${ITER}.mp4"
SRT_FILE="$RUN_DIR/subs_iter${ITER}.srt"

# Naive SRT: chunk text into ~6-word lines, evenly spaced over narration duration
DUR=$(ffprobe -v 0 -of csv=p=0 -show_entries format=duration "$NARRATION_MP3" | python3 -c "import sys; print(int(float(sys.stdin.read())))")
echo "  ⏱ narration duration: ${DUR}s"

python3 - "$SRT_FILE" "$DUR" "$SCRIPT_TEXT" <<'PY'
import sys
out, dur, text = sys.argv[1:4]
dur = int(dur)
words = text.split()
# Aim for ~6 words/line at ~150 wpm = 2.4s/line
chunk_size = 6
chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
if not chunks: chunks = ['(no narration)']
per = dur / len(chunks)
def ts(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f'{h:02d}:{m:02d}:{sec:06.3f}'.replace('.', ',')
lines = []
for i, c in enumerate(chunks):
    lines.append(f'{i+1}\n{ts(i*per)} --> {ts(min((i+1)*per, dur))}\n{c}\n')
open(out,'w').write('\n'.join(lines))
PY

case "$PROD" in
  *still*|*ffmpeg-still*|*flux*ffmpeg-still*)
    echo "  🎬 ffmpeg compose: still-image archetype"
    ffmpeg -y \
      -loop 1 -t "$DUR" -i "$AVATAR_PNG" \
      -i "$NARRATION_MP3" \
      -stream_loop -1 -t "$DUR" -i "$BGM_MP3" \
      -filter_complex "[1:a]volume=1.0[narr];[2:a]volume=0.05[bgm];[narr][bgm]amix=inputs=2:duration=longest[a];[0:v]scale=${SRC_W:-1280}:${SRC_H:-720}:force_original_aspect_ratio=increase,crop=${SRC_W:-1280}:${SRC_H:-720},subtitles='$SRT_FILE':force_style='Fontname=Helvetica,Fontsize=46,PrimaryColour=&Hffffff,Outline=3,OutlineColour=&H000000,Alignment=2,MarginV=140'[v]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k -shortest \
      "$CLONE_MP4" 2>&1 | tail -3
    ;;
  *kling*|*i2v*)
    echo "  🎬 image-to-video archetype (Kling i2v) — TODO: implement, falling back to still"
    ffmpeg -y \
      -loop 1 -t "$DUR" -i "$AVATAR_PNG" \
      -i "$NARRATION_MP3" \
      -stream_loop -1 -t "$DUR" -i "$BGM_MP3" \
      -filter_complex "[1:a]volume=1.0[narr];[2:a]volume=0.05[bgm];[narr][bgm]amix=inputs=2:duration=longest[a];[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,subtitles='$SRT_FILE':force_style='Fontname=Helvetica,Fontsize=46,PrimaryColour=&Hffffff,Outline=3,Alignment=2,MarginV=140'[v]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k -shortest \
      "$CLONE_MP4" 2>&1 | tail -3
    ;;
  *heygen*|*talking-head*)
    echo "  🎬 talking-head archetype (HeyGen) — TODO: implement properly, falling back to still"
    ffmpeg -y \
      -loop 1 -t "$DUR" -i "$AVATAR_PNG" \
      -i "$NARRATION_MP3" \
      -stream_loop -1 -t "$DUR" -i "$BGM_MP3" \
      -filter_complex "[1:a]volume=1.0[narr];[2:a]volume=0.05[bgm];[narr][bgm]amix=inputs=2:duration=longest[a];[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,subtitles='$SRT_FILE':force_style='Fontname=Anton,Fontsize=42,PrimaryColour=&Hffffff,Outline=2,Alignment=2,MarginV=120'[v]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k -shortest \
      "$CLONE_MP4" 2>&1 | tail -3
    ;;
  *)
    echo "  ⚠ unknown production stack '$PROD' — using still-image fallback"
    ffmpeg -y \
      -loop 1 -t "$DUR" -i "$AVATAR_PNG" \
      -i "$NARRATION_MP3" \
      -filter_complex "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,subtitles='$SRT_FILE':force_style='Fontname=Helvetica,Fontsize=46,PrimaryColour=&Hffffff,Outline=3,Alignment=2,MarginV=140'[v]" \
      -map "[v]" -map 1:a -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k -shortest \
      "$CLONE_MP4" 2>&1 | tail -3
    ;;
esac

[ -f "$CLONE_MP4" ] || { echo "❌ ffmpeg failed to produce $CLONE_MP4"; exit 4; }
echo "  ✅ clone_iter${ITER}.mp4 ($(du -h "$CLONE_MP4" | cut -f1))"

# ─── Desktop side-by-side ───────────────────────────────────────────
SOURCE_HANDLE=$(python3 -c "import json; print(json.load(open('$PICKED')).get('author_handle',''))")
DESKTOP_DIR="$HOME/Desktop/anicca-monk-demo/cvff_proofs/${SOURCE_HANDLE}_${SOURCE_ID}"
mkdir -p "$DESKTOP_DIR"
cp "$SOURCE_MP4" "$DESKTOP_DIR/00_original_${SOURCE_ID}.mp4" 2>/dev/null || true
cp "$CLONE_MP4" "$DESKTOP_DIR/clone_iter${ITER}.mp4"
cp "$AVATAR_PNG" "$DESKTOP_DIR/avatar_iter${ITER}.png" 2>/dev/null || true
cp "$CLONE_SPEC" "$DESKTOP_DIR/clone_spec_iter${ITER}.json" 2>/dev/null || true
echo "  📂 Desktop side-by-side: $DESKTOP_DIR"
echo ""
