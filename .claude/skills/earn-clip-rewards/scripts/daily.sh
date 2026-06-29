#!/usr/bin/env bash
# daily.sh — the SCALE loop. One source → EN + JP clips → VERIFY gate → post to
# ALL accounts → submit to reward campaigns → ledger. No-human; run by launchd.
#
#   bash daily.sh "<youtube-url>" ["<hook-en>"] ["<hook-ja>"]
#   bash daily.sh                       # auto-pick a trending single-speaker source
#
# Pipeline (Dais 2026-06-29 'just clip it + caption it', simple = default):
#   yt-dlp 1080p → SamurAIGPT (Gemini rank + face crop) → trim →
#   burn_captions EN + JP → ★ verify_clip.sh GATE (block on fail) ★ →
#   post to X/IG/TikTok (poster.sh) → submit ClipAffiliates → ledger row
#
# ★ The verification loop is INSIDE the skill: a clip that fails verify_clip.sh
#   is NEVER posted. ★
set -euo pipefail

SD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO=~/.cache/anicca-clones/AI-Youtube-Shorts-Generator
PY="$REPO/.venv/bin/python"
OUT=~/clips/daily/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
set -a; source ~/.openclaw/.env; set +a
export GOOGLE_API_KEY="${GEMINI_API_KEY}"
export LOCAL_WHISPER_MODEL=tiny

URL="${1:-}"
HOOK_EN="${2:-}"
HOOK_JA="${3:-}"

# 0) pick source if none given — trending single-speaker money/AI podcast
if [ -z "$URL" ]; then
  URL=$("$PY" -m yt_dlp --flat-playlist --playlist-end 1 --print "%(id)s" \
    "ytsearch1:Diary of a CEO OR My First Million OR Scott Galloway full episode" 2>/dev/null | head -1)
  URL="https://www.youtube.com/watch?v=$URL"
fi
echo "[daily] source = $URL"

# 1) download 1080p (explicit 137 to avoid 360p progressive trap) — a mid 5-min slice
"$PY" -m yt_dlp -f "137+bestaudio[ext=m4a]/best[height<=1080]" --merge-output-format mp4 \
  --download-sections "*15:00-20:00" --force-keyframes-at-cuts \
  -o "$OUT/src.mp4" "$URL"

# 2) SamurAIGPT clip
cd "$REPO"
"$PY" main.py "file://$OUT/src.mp4" --mode local --num-clips 1 --aspect-ratio 9:16 \
  --language en --output-json "$OUT/result.json"
RAWCLIP=$(ls -t "$REPO"/output/short_*.mp4 | head -1)
HOOK_EN="${HOOK_EN:-$("$PY" -c "import json;print(json.load(open('$OUT/result.json'))['highlights'][0].get('hook','')[:60])")}"

# 3) trim to ≤45s
ffmpeg -y -i "$RAWCLIP" -t 45 -c:v libx264 -preset veryfast -crf 20 -c:a aac "$OUT/clip.mp4" 2>/dev/null

# 4) captions EN + JP (simple = default)
"$PY" "$SD/burn_captions.py" "$OUT/clip.mp4" "$OUT/EN.mp4" --hook "$HOOK_EN" --model tiny --lang en
"$PY" "$SD/burn_captions.py" "$OUT/clip.mp4" "$OUT/JP.mp4" --hook "${HOOK_JA:-$HOOK_EN}" --model tiny --lang en --jp

# 5) ★ VERIFY GATE — block any clip that fails ★
for V in EN JP; do
  bash "$SD/verify_clip.sh" "$OUT/$V.mp4" || { echo "[daily] BLOCKED: $V failed verification — not posting" >&2; exit 2; }
done

# 6) post to all accounts + submit (poster.sh handles per-platform; ledger appended)
#    poster.sh is the post-Postiz custom poster (TODO: build per-platform CDP posters)
if [ -x "$SD/poster.sh" ]; then
  bash "$SD/poster.sh" "$OUT/EN.mp4" en "$HOOK_EN" || echo "[daily] poster EN returned non-zero"
  bash "$SD/poster.sh" "$OUT/JP.mp4" ja "${HOOK_JA:-$HOOK_EN}" || echo "[daily] poster JP returned non-zero"
else
  echo "[daily] poster.sh not built yet — clips verified + staged at $OUT (manual post)"
fi

# 7) ledger row
LEDGER=~/.smtm/earn-loops/clip/ledger.jsonl
mkdir -p "$(dirname "$LEDGER")"
printf '{"ts":"%s","source":"%s","hook_en":"%s","en":"%s","jp":"%s","status":"verified"}\n' \
  "$(date -u +%FT%TZ)" "$URL" "$HOOK_EN" "$OUT/EN.mp4" "$OUT/JP.mp4" >> "$LEDGER"

# 8) disk hygiene — drop the big source
rm -f "$OUT/src.mp4" "$REPO"/output/source_*.mp4 2>/dev/null || true
echo "[daily] DONE → $OUT (EN.mp4 + JP.mp4 verified)"
