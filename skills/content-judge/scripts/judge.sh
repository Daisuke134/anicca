#!/usr/bin/env bash
# Pre-post QA gate. Returns OK on stdout / exit 0, or NG: <reason> / exit 1.
# Usage: judge.sh <mp4> <ass_or_-> <caption_text> <lang>
set -euo pipefail
MP4="${1:?usage: judge.sh <mp4> <ass_or_-> <caption> <lang>}"
ASS="${2:?}"
CAPTION="${3:?}"
LANG_ARG="${4:?}"

ROOT="$HOME/anicca-monk-factory"
set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a

if [ "${CONTENT_JUDGE_ENABLED:-false}" != "true" ]; then
  echo "OK"
  exit 0
fi

if [ ! -f "$MP4" ]; then
  echo "NG: mp4 not found: $MP4"
  exit 1
fi

WORK=$(mktemp -d)
trap "rm -rf $WORK" EXIT

# Extract 5 evenly-spaced frames
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MP4" 2>/dev/null | head -c 6)
if [ -z "$DURATION" ]; then
  echo "NG: cannot read mp4 duration"; exit 1
fi
INTERVAL=$(python3 -c "print($DURATION/6)")
ffmpeg -y -i "$MP4" -vf "fps=1/$INTERVAL,scale=480:-1" -frames:v 5 "$WORK/frame_%02d.jpg" -loglevel error 2>&1 || {
  echo "NG: ffmpeg frame extraction failed"; exit 1
}

# Encode to base64 for gpt vision
export WORK CAPTION LANG_ARG
RESULT=$(python3 - <<'PY'
import os, json, base64, urllib.request, glob

work = os.environ['WORK']
caption = os.environ['CAPTION']
lang = os.environ['LANG_ARG']
key = os.environ.get('OPENAI_API_KEY')
if not key:
    print('OK')
    exit(0)

frames = sorted(glob.glob(f'{work}/frame_*.jpg'))[:5]
if not frames:
    print('NG: no frames extracted')
    exit(1)

content = [
    {'type': 'text', 'text': f'''You are a pre-post QA judge for a TikTok video. Lang={lang}.

Caption being used:
{caption}

5 frames from the video are attached. Check:
1. Face distortion (eyes off, mouth glitch, deformed features)
2. Caption text on screen visible without truncation
3. Anything obviously broken (frozen frame, black frame, glitchy avatar)

Then check the caption text for:
- Banned tags (TikTok forbids spam-y combos; IG bans #fyp)
- URL typos (aniccaai.com is correct)
- Anything against guidelines

Reply EXACTLY one of:
OK
NG: <one-line reason>'''}
]
for f in frames:
    b64 = base64.b64encode(open(f, 'rb').read()).decode()
    content.append({'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}})

req = urllib.request.Request(
    'https://api.openai.com/v1/chat/completions',
    data=json.dumps({
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': content}],
        'max_tokens': 200
    }).encode(),
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read().decode())['choices'][0]['message']['content'].strip()
except Exception as e:
    print(f'OK')  # fail open — don't block posts on API errors
    exit(0)

# Normalize
first_line = out.split('\n')[0].strip()
if first_line.upper().startswith('OK'):
    print('OK')
else:
    print(first_line if first_line.upper().startswith('NG') else f'NG: {first_line[:120]}')
PY
)

echo "$RESULT"
if echo "$RESULT" | head -1 | grep -qi '^NG'; then
  exit 1
fi
exit 0
