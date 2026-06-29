#!/usr/bin/env bash
set -euo pipefail
REPO=~/.cache/anicca-clones/AI-Youtube-Shorts-Generator
SK=~/.claude/skills/embedded-captions
EC=~/.claude/skills/earn-clip-rewards
PROJ=~/clips/ec-galloway-hd
PY="$REPO/.venv/bin/python"
set -a; source ~/.openclaw/.env; set +a
export GOOGLE_API_KEY="$GEMINI_API_KEY"
export LOCAL_WHISPER_MODEL=tiny
export HYPERFRAMES_ROOT=~/.cache/hyperframes-root

echo "[1] SamurAIGPT on 1080p source"
cd "$REPO"
"$PY" main.py "file://$HOME/clips/demo3/galloway1080.mp4" --mode local --num-clips 1 \
  --aspect-ratio 9:16 --language en --output-json ~/clips/demo3/hd_result.json
CLIP=$(ls -t "$REPO"/output/short_*.mp4 | head -1)
echo "[1] clip = $CLIP  dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$CLIP")"

echo "[2] trim to 45s"
mkdir -p "$PROJ"
ffmpeg -y -i "$CLIP" -t 45 -c:v libx264 -preset veryfast -crf 20 -c:a aac "$PROJ/source.mp4" 2>/dev/null
echo "[2] source dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$PROJ/source.mp4")"

echo "[3] prepare (matte + transcribe + safe-zones)"
bash "$SK/scripts/prepare.sh" "$PROJ"
node "$SK/scripts/safe-zones.cjs" "$PROJ"

echo "[4] author theme.json (anchor)"
W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$PROJ/source.mp4")
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$PROJ/source.mp4")
"$PY" - "$PROJ" "$W" "$H" <<'PY'
import json, re, sys
proj, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
t=json.load(open(f"{proj}/transcript.json"))
words=[w["text"].strip() for w in t["words"]]
def norm(s): return re.sub(r"[^a-z0-9']",'',s.lower())
# pick a 2-word hero present in transcript: prefer a punchy noun pair near the middle
cands=[("catch","rockets"),("deliver","magic"),("the","future"),("cheap","capital")]
idx=-1; hero=None
for h in cands:
    hn=[norm(x) for x in h]
    for i in range(len(words)-1):
        if [norm(words[i]),norm(words[i+1])]==hn: idx=i; hero=h; break
    if idx>=0: break
if idx<0:
    idx=len(words)//2; hero=(words[idx],words[idx+1])
pre=words[:idx]; post=words[idx+2:]
def chunk(ws):
    L=[];c=[]
    for w in ws:
        c.append(w)
        if re.search(r'[.?!]$',w) or len(c)>=5: L.append(c);c=[]
    if c: L.append(c)
    return L
lines=chunk(pre)+chunk(post)
theme={"dna":"anchor","lines":lines,"hero":{"match":" ".join(hero)},"width":W,"height":H}
json.dump(theme,open(f"{proj}/theme.json","w"),ensure_ascii=False,indent=2)
print(f"[4] hero={' '.join(hero)} lines={len(lines)} {W}x{H}")
PY

echo "[5] make-theme + render"
node "$SK/scripts/make-theme.cjs" "$PROJ"
bash "$SK/scripts/render-theme.sh" "$PROJ"
echo "[DONE] $PROJ/final_fx.mp4"
ls -la "$PROJ/final_fx.mp4"
