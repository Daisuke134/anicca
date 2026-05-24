#!/usr/bin/env bash
# Burn Yang-Mun-style captions into a HeyGen-rendered talking-head mp4.
# Usage: burn-captions.sh <input.mp4> <output.mp4>
# Style (matched to real @yangmun2): CENTER, 2-word UPPERCASE chunks, white + ONE yellow keyword,
#   heavy font (TikTok Sans Display Black), word-synced via whisper word timestamps. Verified 2026-05-23.
set -euo pipefail
IN="$1"; OUT="$2"
[ -f "$IN" ] || { echo "FATAL: input not found: $IN"; exit 1; }
SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"
CAPDIR="$HOME/anicca-monk-factory/captions"; mkdir -p "$CAPDIR"
BASE="$(basename "$IN" .mp4)"
FONTS="$HOME/Library/Fonts"   # has TikTokSansDisplayBlack.ttf

echo "[1/3] whisper word-level transcription"
whisper "$IN" --model base --language en --word_timestamps True \
  --output_format json --output_dir "$CAPDIR/" >/dev/null 2>&1
[ -f "$CAPDIR/$BASE.json" ] || { echo "FATAL: whisper json missing"; exit 1; }

echo "[2/3] build .ass (2-word chunks, center, yellow keyword)"
python3 "$SKILL/scripts/build_ass.py" "$CAPDIR/$BASE.json" "$CAPDIR/$BASE.ass" 2 0.0

echo "[3/3] ffmpeg burn"
ffmpeg -y -v error -i "$IN" -vf "subtitles=$CAPDIR/$BASE.ass:fontsdir=$FONTS" -c:a copy "$OUT"
[ -f "$OUT" ] || { echo "FATAL: ffmpeg output missing"; exit 1; }

# VERIFY (#8): sample frames at fixed times vs whisper words → confirm sync, and confirm captions visible
echo "VERIFY: sampling sync frames"
SYNC="$HOME/anicca-monk-factory/cap_sync_$BASE"; rm -rf "$SYNC"; mkdir -p "$SYNC"
for t in 10 30 50; do ffmpeg -v error -ss $t -i "$OUT" -frames:v 1 -vf "scale=300:-1" "$SYNC/t${t}.jpg" 2>/dev/null || true; done
python3 - "$CAPDIR/$BASE.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); ws=[w for s in d['segments'] for w in s.get('words',[])]
for t in (10,30,50):
    cur=[w['word'].strip() for w in ws if w['start']<=t<=w['end']] or [w['word'].strip() for w in ws if abs(w['start']-t)<0.6]
    print(f"  t={t}s spoken≈ {cur[:3]}")
PY
echo "BURN_DONE out=$OUT (open the t*.jpg in $SYNC to eyeball caption position vs spoken word)"
