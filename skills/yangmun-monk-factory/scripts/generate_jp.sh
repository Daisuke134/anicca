#!/usr/bin/env bash
# JP pipeline: OpenAI TTS Onyx → 5 fal Kling clips → concat → Whisper segments → ASS per-phrase subs (DP-aligned) → final mp4
# Reads bank_jp.jsonl entry's `phrases` field as source of truth.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a
export PATH="$HOME/.local/bin:$PATH"

TS=$(date +%Y%m%d_%H%M%S)
WORK="$ROOT/renders/jp_${TS}"
mkdir -p "$WORK"
export WORK ROOT TS

# Pull script + phrases from current_jp.json
SCRIPT_TEXT=$(python3 - <<'PY'
import json, os
d = json.load(open(os.path.expanduser('~/anicca-monk-factory/state/current_jp.json'), encoding='utf-8'))
print(d.get('full_text',''), end='')
PY
)
export SCRIPT_TEXT

# 1) TTS — ElevenLabs (preferred) or OpenAI fallback. Provider via $JP_TTS_PROVIDER env.
JP_PROVIDER="${JP_TTS_PROVIDER:-elevenlabs}"
if [ "$JP_PROVIDER" = "elevenlabs" ] && [ -n "${ELEVENLABS_API_KEY:-}" ] && [ -n "${JP_TTS_VOICE_ID:-}" ]; then
  echo "🗣 ElevenLabs TTS (${JP_TTS_VOICE_NAME:-bill})..." >&2
  TTS_PAYLOAD=$(python3 - <<'PY'
import json, os
print(json.dumps({
  'text': os.environ['SCRIPT_TEXT'],
  'model_id': os.environ.get('JP_TTS_MODEL', 'eleven_multilingual_v2'),
  'voice_settings': {'stability': 0.55, 'similarity_boost': 0.75, 'style': 0.3, 'use_speaker_boost': True}
}))
PY
)
  curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/${JP_TTS_VOICE_ID}" \
    -H "xi-api-key: $ELEVENLABS_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$TTS_PAYLOAD" \
    --output "$WORK/narration.mp3"
else
  echo "🗣 OpenAI Onyx TTS (fallback)..." >&2
  TTS_PAYLOAD=$(python3 - <<'PY'
import json, os
print(json.dumps({
  'model': 'tts-1-hd',
  'input': os.environ['SCRIPT_TEXT'],
  'voice': 'onyx',
  'speed': 1.0,
  'response_format': 'mp3'
}))
PY
)
  curl -sS -X POST "https://api.openai.com/v1/audio/speech" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$TTS_PAYLOAD" \
    --output "$WORK/narration.mp3"
fi

AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WORK/narration.mp3")
echo "  audio: ${AUDIO_DUR}s" >&2

# 2) Submit 5 Kling jobs in parallel
echo "🎞 fal Kling 5 clips..." >&2
for i in 01 02 03 04 05; do
  CACHED="$ROOT/state/jp_url_$i.txt"
  [ -f "$CACHED" ] || { echo "❌ missing $CACHED — refs not uploaded" >&2; exit 4; }
  IMG_URL=$(cat "$CACHED")
  case $i in
    01) MOTION="gentle subtle breathing motion, soft eyes closing and opening slowly, sakura petals drifting down softly" ;;
    02) MOTION="slight head tilt up looking at sky with peaceful smile, gentle wind in robe, cherry petals drifting" ;;
    03) MOTION="meditative breathing motion, soft eye movement, dappled sunlight gently shifting through bamboo" ;;
    04) MOTION="standing still by the stream, gentle water reflection movement, soft breeze, calm gaze" ;;
    05) MOTION="hands together in gassho prayer, slight bow forward, sunset light shifting warmly" ;;
  esac
  export IMG_URL MOTION
  KLING_PAYLOAD=$(python3 - <<'PY'
import json, os
print(json.dumps({'image_url': os.environ['IMG_URL'], 'prompt': os.environ['MOTION'], 'duration': '5', 'aspect_ratio': '9:16'}))
PY
)
  RESP=$(curl -sS -X POST "https://queue.fal.run/fal-ai/kling-video/v2.5-turbo/standard/image-to-video" \
    -H "Authorization: Key $FAL_KEY" -H "Content-Type: application/json" \
    -d "$KLING_PAYLOAD")
  REQ=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('request_id',''))")
  echo "$REQ" > "$WORK/kling_$i.txt"
done

# Poll all
for i in 01 02 03 04 05; do
  REQ=$(cat "$WORK/kling_$i.txt")
  for n in $(seq 1 80); do
    STAT=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ/status" -H "Authorization: Key $FAL_KEY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo '')
    if [ "$STAT" = "COMPLETED" ]; then
      VURL=$(curl -sS "https://queue.fal.run/fal-ai/kling-video/requests/$REQ" -H "Authorization: Key $FAL_KEY" | python3 -c "import json,sys; print(json.load(sys.stdin)['video']['url'])")
      curl -sS -o "$WORK/clip_$i.mp4" "$VURL"
      echo "  clip $i ✅" >&2
      break
    fi
    sleep 8
  done
done

# 3) Concat — loop the 5×5s clips to fill full audio duration (audio can run 60-100s)
echo "🔗 concat (loop to fill audio)..." >&2
for i in 01 02 03 04 05; do echo "file 'clip_$i.mp4'"; done > "$WORK/concat.txt"
VIDEO_DUR=$(python3 -c "print(${AUDIO_DUR} + 0.5)")
ffmpeg -y -stream_loop -1 -f concat -safe 0 -i "$WORK/concat.txt" -c:v libx264 -preset medium -crf 22 -an -t "$VIDEO_DUR" "$WORK/concat.mp4" 2>/dev/null

# 4) Whisper word-level for accurate phrase alignment
python3 - <<'PY'
import os, whisper, json
m = whisper.load_model('base')
r = m.transcribe(os.path.join(os.environ['WORK'],'narration.mp3'), word_timestamps=True, language='ja', fp16=False)
words = []
for seg in r['segments']:
    for w in seg.get('words', []):
        words.append({'word': w['word'].strip(), 'start': float(w['start']), 'end': float(w['end'])})
json.dump(words, open(os.path.join(os.environ['WORK'],'words.json'),'w'), ensure_ascii=False, indent=2)
PY

# 5) Build ASS — bank phrases are TRUTH, Whisper words give timestamps via DP alignment
python3 - <<'PY'
import os, json, re
WORK = os.environ['WORK']
ROOT = os.environ['ROOT']
words = json.load(open(os.path.join(WORK, 'words.json')))
d = json.load(open(os.path.join(ROOT, 'state', 'current_jp.json'), encoding='utf-8'))
phrases = d.get('phrases') or [d.get('full_text','')]
audio_end = max((w['end'] for w in words), default=0)

# Use sequential character-count proportional alignment to map phrases to time
# Each phrase gets duration proportional to its length
total_chars = sum(max(len(p.replace('「','').replace('」','').replace('…','').replace('。','').replace('、','')), 1) for p in phrases)
# Build cumulative phrase positions in source text (without spaces)
src_concat = ''.join(phrases)
# Stream Whisper words and assign each phrase its time based on cumulative chars
char_per_sec = total_chars / audio_end if audio_end > 0 else 1
mapped = []
cumulative_chars = 0
for p in phrases:
    p_clean_len = len(p.replace('「','').replace('」','').replace('…','').replace('。','').replace('、','').strip())
    p_len = max(p_clean_len, 1)
    start_t = cumulative_chars / char_per_sec if char_per_sec > 0 else 0
    cumulative_chars += p_len
    end_t = cumulative_chars / char_per_sec if char_per_sec > 0 else audio_end
    mapped.append((p, start_t, end_t))

# STRICT non-overlap: each phrase ends EXACTLY where the next begins
# → only 1 phrase visible at any moment, max 2 wrap-lines, never 4
def snap(t, words):
    if not words: return t
    return min(words, key=lambda w: abs(w['start']-t))['start']

# Step 1: snap phrase START times to whisper word boundaries
starts = []
for i,(p,s,e) in enumerate(mapped):
    rs = snap(s, words)
    if i > 0:
        rs = max(rs, starts[-1] + 0.4)
    starts.append(rs)

# Step 2: phrase[i].end = phrase[i+1].start (no overlap, hard cut)
refined = []
for i, (p, _s, _e) in enumerate(mapped):
    rs = starts[i]
    re_ = starts[i+1] if i+1 < len(starts) else audio_end
    if re_ <= rs:
        re_ = rs + 0.4
    refined.append((p, rs, re_))

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
Style: JP,Hiragino Kaku Gothic ProN,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

# JP-6 (2026-05-04): tokenize kanji phrase with janome → convert each word to hiragana via pykakasi.
# Yields word-bounded hiragana display. NEVER break mid-word. Each scene ≤ 36 chars / 2 lines.
from janome.tokenizer import Tokenizer
import pykakasi
_tok = Tokenizer()
_kks = pykakasi.kakasi()

# Override map for single-kanji compound mistakes pykakasi makes in isolation
HIRA_OVERRIDE = {
    '重': 'おも',  # 重さ→おもさ (default reading じゅう wrong here)
    '苦': 'くる',  # 苦しみ→くるしみ (wrong if alone)
    '間': 'あいだ',  # 時間文脈ではない isolated 間
    '人': 'ひと',
    '時': 'とき',
}

def to_hira_word(surface):
    if surface in HIRA_OVERRIDE:
        return HIRA_OVERRIDE[surface]
    return ''.join(r['hira'] for r in _kks.convert(surface))

# Particles that visually cling to the previous word — never start a line.
GLUE_BACK_PARTICLES = set(['て','た','だ','に','で','を','が','は','と','の','も','ね','よ','さ','し','か'])

def tokenize_hira_words(phrase):
    """Tokenize kanji phrase, hiragana-convert each word, then glue trailing single-particle
       tokens to the preceding word so 立ち止まっ\\Nて does not happen."""
    raw = [to_hira_word(t.surface) for t in _tok.tokenize(phrase)]
    out = []
    for w in raw:
        if w in GLUE_BACK_PARTICLES and out and out[-1] not in '、。?!…':
            out[-1] = out[-1] + w
        else:
            out.append(w)
    return out

def pack_scenes(hira_words, max_per_line=18):
    """Greedy line-pack: each scene = (line1_words, line2_words) where each line ≤ max_per_line.
       A new scene starts when neither line can fit the next word."""
    scenes = []
    l1, l2, n1, n2 = [], [], 0, 0
    for w in hira_words:
        ln = len(w)
        if not l2 and n1 + ln <= max_per_line:
            l1.append(w); n1 += ln
        elif n2 + ln <= max_per_line:
            l2.append(w); n2 += ln
        else:
            scenes.append((l1, l2))
            l1, l2, n1, n2 = [w], [], ln, 0
    if l1 or l2:
        scenes.append((l1, l2))
    return scenes

def fmt_scene(l1_words, l2_words):
    s1 = ''.join(l1_words); s2 = ''.join(l2_words)
    return s1 + ('\\N' + s2 if s2 else '')

for txt, s, e in refined:
    txt = txt.replace('\n', ' ').strip()
    hira_words = tokenize_hira_words(txt)
    scenes = pack_scenes(hira_words, max_per_line=18)
    if not scenes:
        continue
    total = sum(sum(len(w) for w in (l1+l2)) for (l1,l2) in scenes) or 1
    cum = 0
    for (l1, l2) in scenes:
        sub_s = s + (e - s) * (cum / total)
        cum += sum(len(w) for w in (l1+l2))
        sub_e = s + (e - s) * (cum / total)
        if sub_e <= sub_s:
            sub_e = sub_s + 0.4
        ass += f'Dialogue: 0,{t(sub_s)},{t(sub_e)},JP,,0,0,380,,{fmt_scene(l1,l2)}\n'
open(os.path.join(WORK, 'subs.ass'), 'w', encoding='utf-8').write(ass)
PY

# 6) Final assemble — JP-4 fix: tpad freezes last frame for 4s so video > audio always.
# This guarantees audio is never cut off by -shortest. The visible result: tail freeze for ~0.5-1s after last word, then natural cut.
FINAL="$ROOT/renders/jp_${TS}_final.mp4"
ffmpeg -y -i "$WORK/concat.mp4" -i "$WORK/narration.mp3" \
  -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=4,subtitles=$WORK/subs.ass[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset medium -crf 22 -c:a aac -b:a 192k -shortest \
  "$FINAL" 2>/dev/null

echo "$FINAL"
