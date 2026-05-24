#!/usr/bin/env bash
# EN pipeline: HeyGen Avatar IV → Whisper word timestamps → ASS karaoke subs → final mp4
# Outputs ~/anicca-monk-factory/renders/en_<TS>_final.mp4 path on stdout.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a
export PATH="$HOME/.local/bin:$PATH"

TS=$(date +%Y%m%d_%H%M%S)
RAW="$ROOT/renders/en_${TS}_raw.mp4"
SUBS="$ROOT/renders/en_${TS}_subs.ass"
WORDS="$ROOT/renders/en_${TS}_words.json"
FINAL="$ROOT/renders/en_${TS}_final.mp4"

# Read script text + apply pronunciation hints for TTS (display vs spoken)
SCRIPT_TEXT=$(python3 - <<'PY'
import json
d = json.load(open(__import__('os').path.expanduser('~/anicca-monk-factory/state/current_en.json'), encoding='utf-8'))
print(d.get('full_text') or ' '.join(filter(None, [d.get('hook',''), d.get('body',''), d.get('close','')])), end='')
PY
)
# Spoken-form preprocessing:
#   1) "Anicca Monk" → "Achan"    (locked identity rename, applies to legacy bank entries)
#   2) "Anicca"      → "Anicha"   (concept word, ah-NEE-cha)
#   3) "Achan"       → "Ahchan"   (TTS hint for matcha-like ah-CHA-n)
TTS_TEXT=$(echo "$SCRIPT_TEXT" | sed 's/Anicca Monk/Achan/g; s/Anicca/Aneetcha/g; s/Achan/Ahchan/g')
export SCRIPT_TEXT TTS_TEXT

# CACHED LIBRARY MODE (CA1 2026-05-08, Locked Asset Rule)
# preload-bank-library.sh generates 1 HeyGen Avatar IV mp4 per bank entry ONCE.
# Daily cron just rotates entries → cp cached → ffmpeg subs+BGM → Postiz. $0/render.
# Re-run preload-bank-library.sh when bank gets new entries (winner-analyzer hook).
EID=$(python3 -c "
import json, os
d = json.load(open(os.path.expanduser('~/anicca-monk-factory/state/current_en.json'), encoding='utf-8'))
print(d.get('id',''))
")
CACHED_VID="$ROOT/state/cached_${EID}.mp4"
if [ ! -f "$CACHED_VID" ] || [ ! -s "$CACHED_VID" ]; then
  echo "❌ no cached video for entry '$EID' at $CACHED_VID" >&2
  echo "   Run: bash ~/.openclaw/skills/yangmun-monk-factory/scripts/preload-bank-library.sh" >&2
  exit 5
fi
echo "  ✅ using cached library: $(basename "$CACHED_VID") ($(du -h "$CACHED_VID" | cut -f1))" >&2
cp "$CACHED_VID" "$RAW"

# 1.5) Cinematic hook prefix (Shalev pattern: Kling 2-3s scroll-stopper before HeyGen body).
# Disabled by default; opt-in via EN_CINEMATIC_HOOK=1.
if [ "${EN_CINEMATIC_HOOK:-0}" = "1" ]; then
  HOOK_MOTION=$(python3 -c "
import json, os
d = json.load(open(os.path.expanduser('~/anicca-monk-factory/state/current_en.json'), encoding='utf-8'))
print(d.get('hook_motion', 'elderly Theravada monk in saffron robe walking out of misty temple corridor, slowly turning toward camera, peaceful smile'))
")
  SKILL_DIR="$(dirname "$0")"
  HOOK=$(bash "$SKILL_DIR/cinematic_hook.sh" "$HOOK_MOTION" 3 2>/dev/null || true)
  if [ -n "$HOOK" ] && [ -f "$HOOK" ]; then
    COMBINED="${RAW%.mp4}_combined.mp4"
    # Concat: hook (3s, no audio) + body (HeyGen mp4 with audio). Pad hook silence to keep audio sync.
    ffmpeg -y -i "$HOOK" -i "$RAW" \
      -filter_complex "[0:v]scale=720:1280:force_original_aspect_ratio=cover,crop=720:1280[h0];anullsrc=channel_layout=stereo:sample_rate=44100[h0a];[h0][h0a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 22 -c:a aac -b:a 192k "$COMBINED" 2>/dev/null \
        && mv "$COMBINED" "$RAW"
    echo "  ✅ cinematic hook prepended" >&2
  fi
fi

# 2) Whisper word-level
export RAW
python3 - <<'PY'
import os, whisper, json
m = whisper.load_model('base.en')
r = m.transcribe(os.environ['RAW'], word_timestamps=True, fp16=False)
out = []
for seg in r['segments']:
  for w in seg.get('words', []):
    out.append({'word': w['word'].strip(), 'start': float(w['start']), 'end': float(w['end'])})
json.dump(out, open(os.environ['RAW'].replace('_raw.mp4','_words.json'),'w'), indent=2)
PY

# 3) Build ASS (2-word chunks; emphasis from bank's emphasis_words)
export WORDS SUBS
python3 - <<'PY'
import os, json
words = json.load(open(os.environ['WORDS']))
d = json.load(open(os.path.expanduser('~/anicca-monk-factory/state/current_en.json'), encoding='utf-8'))
emph_set = set(w.lower() for w in d.get('emphasis_words', []))

def is_emph(w):
    return w.strip(".,!?\"'-").lower() in emph_set

chunks = []
i = 0
while i < len(words):
    a = words[i]
    b = words[i+1] if i+1 < len(words) else None
    if b:
        aw_e = is_emph(a['word'])
        bw_e = is_emph(b['word'])
        if aw_e and not bw_e:
            emph = 0  # word A yellow
        elif bw_e and not aw_e:
            emph = 1  # word B yellow
        elif aw_e and bw_e:
            emph = 1  # both eligible, prefer second (often more prominent)
        else:
            emph = 1  # neither in list, fall back to second word yellow
        chunks.append((a['word'].strip(), b['word'].strip(), a['start'], b['end'], emph))
        i += 2
    else:
        chunks.append((a['word'].strip(), '', a['start'], a['end'], 0))
        i += 1
def t(s):
    h = int(s//3600); m = int((s%3600)//60); sec = s%60
    return f'{h:01d}:{m:02d}:{sec:05.2f}'
ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: White,Arial Black,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
for w0, w1, s, e, emph in chunks:
    if not w1:
        text = '{\\c&H00FFFFFF&}' + w0
    elif emph == 0:
        text = '{\\c&H0000D7FF&}' + w0 + '{\\c&H00FFFFFF&} ' + w1
    else:
        text = '{\\c&H00FFFFFF&}' + w0 + ' {\\c&H0000D7FF&}' + w1
    ass += f'Dialogue: 0,{t(s)},{t(e)},White,,0,0,300,,{text}\n'
open(os.environ['SUBS'], 'w', encoding='utf-8').write(ass)
PY

# 4) Burn subs + mix BGM at -18dB (yangmun2 has audible BGM throughout)
BGM="$ROOT/assets/bgm/charlie_sky_mindfulness.mp3"
FONTS_DIR="$ROOT/assets/fonts"
if [ -f "$BGM" ]; then
  ffmpeg -y -i "$RAW" -stream_loop -1 -i "$BGM" \
    -filter_complex "[1:a]volume=0.05[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a];[0:v]subtitles=$SUBS:fontsdir=$FONTS_DIR[v]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 22 -c:a aac -b:a 192k "$FINAL" 2>/dev/null
else
  ffmpeg -y -i "$RAW" -filter_complex "[0:v]subtitles=$SUBS:fontsdir=$FONTS_DIR[v]" -map "[v]" -map 0:a \
    -c:v libx264 -preset medium -crf 22 -c:a aac -b:a 192k "$FINAL" 2>/dev/null
fi

echo "$FINAL"
