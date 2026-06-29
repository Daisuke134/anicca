#!/usr/bin/env bash
# burn-captions.sh <in.mp4> <out.mp4> [lang]
# Transcribe the video's audio with openai-whisper (base, cached), group words into short
# cues, and burn TikTok-style centered captions. $0 (local whisper). Rebuilt 2026-06-28 after
# the original was lost; replaces the missing burn step in run-daily.sh.
set -euo pipefail
IN="${1:?in.mp4 required}"; OUT="${2:?out.mp4 required}"; LANG_CODE="${3:-en}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# 1) word-level timestamps (model cached in ~/.cache/whisper → no download)
whisper "$IN" --model base --language "$LANG_CODE" --word_timestamps True \
  --initial_prompt "Anicca, impermanence, dharma, mindfulness, Buddha, breath, suffering, stillness." \
  --output_format json --output_dir "$WORK" --verbose False >/dev/null 2>&1 || true
JSON="$WORK/$(basename "${IN%.*}").json"
[ -s "$JSON" ] || { echo "WHISPER_FAILED" >&2; exit 3; }

# 2) build ASS (centered, bold, 3-4 words per cue)
python3 - "$JSON" "$WORK/subs.ass" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
words = []
for seg in j.get('segments', []):
    for w in seg.get('words', []):
        tx = w.get('word', '').strip()
        if tx:
            words.append((float(w['start']), float(w['end']), tx))
cues = []
i = 0
while i < len(words):
    grp = words[i:i+3]
    cues.append((grp[0][0], grp[-1][1], ' '.join(x[2] for x in grp)))
    i += 3
def t(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h:d}:{m:02d}:{sec:05.2f}"
header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap, Arial, 60, &H00FFFFFF, &H00000000, &H80000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 5, 2, 2, 80, 80, 380, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [header]
for st, en, tx in cues:
    lines.append(f"Dialogue: 0,{t(st)},{t(en)},Cap,,0,0,0,,{tx.upper()}")
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(f"cues={len(cues)}")
PY

# 3) burn
ffmpeg -y -i "$IN" -vf "subtitles=${WORK}/subs.ass" -c:v libx264 -preset medium -crf 20 \
  -pix_fmt yuv420p -c:a copy "$OUT" 2>/dev/null
[ -s "$OUT" ] || { echo "BURN_FAILED" >&2; exit 6; }
echo "BURN_DONE=${OUT}"
