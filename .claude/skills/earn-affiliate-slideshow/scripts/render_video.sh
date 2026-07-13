#!/bin/bash
# render_video.sh — composed_<n>.png + per-slide VOICEVOX narration → 9:16 mp4 (+bg music)
# Usage: render_video.sh <work_dir> <deck.json> <out.mp4>
# Env: VOICEVOX_API_KEY, VOICEVOX_SPEAKER (default 13 = 青山龍星)
set -uo pipefail
WORK="$1"; DECK="$2"; OUT="$3"
SPEAKER="${VOICEVOX_SPEAKER:-13}"
MUSIC="$HOME/.openclaw/skills/anicca-slideshow-to-video/assets/music/affirmation-bg.mp3"
TMP="$WORK/_render"; rm -rf "$TMP"; mkdir -p "$TMP"

# 1. per-slide narration via VOICEVOX cloud → measure duration → make a clip
n=$(python3 -c "import json;print(len(json.load(open('$DECK'))['slides']))")
: > "$TMP/concat.txt"
for i in $(seq 1 "$n"); do
  TXT=$(python3 -c "import json;print(json.load(open('$DECK'))['slides'][$i-1]['narration'])")
  curl -sS -G "https://api.su-shiki.com/v2/voicevox/audio/" \
    --data-urlencode "text=$TXT" --data-urlencode "speaker=$SPEAKER" \
    --data-urlencode "key=$VOICEVOX_API_KEY" --output "$TMP/a_$i.wav"
  # pad 0.6s tail so narration doesn't clip the slide change
  ffmpeg -y -i "$TMP/a_$i.wav" -af "apad=pad_dur=0.6" "$TMP/a_$i.mp3" 2>/dev/null
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/a_$i.mp3")
  # min 3s per slide for readability
  DUR=$(python3 -c "print(max(3.0, float('$DUR')))")
  ffmpeg -y -loop 1 -i "$WORK/composed_$i.png" -i "$TMP/a_$i.mp3" \
    -c:v libx264 -t "$DUR" -pix_fmt yuv420p -vf "scale=1080:1920,fps=30" \
    -c:a aac -b:a 192k -shortest "$TMP/clip_$i.mp4" 2>/dev/null
  echo "file '$TMP/clip_$i.mp4'" >> "$TMP/concat.txt"
  echo "slide $i: ${DUR}s"
done

# 2. concat all clips
ffmpeg -y -f concat -safe 0 -i "$TMP/concat.txt" -c copy "$TMP/novoice_bg.mp4" 2>/dev/null || \
ffmpeg -y -f concat -safe 0 -i "$TMP/concat.txt" -c:v libx264 -c:a aac "$TMP/novoice_bg.mp4" 2>/dev/null

# 3. mix bg music under the narration (music -18dB), if music exists
if [ -f "$MUSIC" ]; then
  ffmpeg -y -i "$TMP/novoice_bg.mp4" -stream_loop -1 -i "$MUSIC" \
    -filter_complex "[1:a]volume=0.12[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$OUT" 2>/dev/null
else
  cp "$TMP/novoice_bg.mp4" "$OUT"
fi
echo "OUT=$OUT"
