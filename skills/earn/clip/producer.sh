#!/usr/bin/env bash
# producer.sh — CLIP-G: the FUEL. Produce ONE fresh captioned 9:16 clip from a long-form
# source and drop it (mp4 + caption.txt) into ~/clips/queue for the loop to post. Posting is
# NOT done here (that's the earn/clip slot's job). Heavy (yt-dlp + whisper + Gemini + crop +
# burn) → run as a DAILY producer cron, separate from the hourly post loop.
#
# Reuses the proven engine: ~/.cache/anicca-clones/AI-Youtube-Shorts-Generator (pipeline.py,
# burn_captions.py, verify_clip.sh) via the earn-clip-rewards skill scripts.
#
#   producer.sh --url <youtube_long_form>   # produce from a specific source
#   producer.sh                              # pick a trending money/AI long-form (engine default)
# Disk hygiene (HARD 0.26): all heavy intermediates go in a /tmp workdir, removed at the end;
# only the final verified mp4 + caption land in ~/clips/queue.
set -uo pipefail
SKILLS="$HOME/.claude/skills/earn-clip-rewards/scripts"
ENGINE="$HOME/.cache/anicca-clones/AI-Youtube-Shorts-Generator"
PY="$ENGINE/.venv/bin/python"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_instance_paths.sh"
QUEUE="$CLIP_QUEUE"; mkdir -p "$QUEUE"
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
export LOCAL_WHISPER_MODEL=tiny
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-${GEMINI_API_KEY:-}}"

URL=""; [ "${1:-}" = "--url" ] && URL="${2:-}"
emit(){ printf '{"producer":"clip","did":%s}\n' "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo "\"$1\"")"; }

[ -x "$PY" ] || { emit "engine venv missing ($PY)"; exit 0; }

# pick a trending single-speaker money/AI long-form if no url (engine's channel default)
if [ -z "$URL" ]; then
  VID=$("$PY" -m yt_dlp --flat-playlist --playlist-end 1 --print "%(id)s" \
        "https://www.youtube.com/@theDiaryOfACEO/videos" 2>/dev/null | head -1)
  [ -n "$VID" ] && URL="https://www.youtube.com/watch?v=$VID"
fi
[ -n "$URL" ] || { emit "no source url"; exit 0; }

WORK="/tmp/clip-producer-$$"; mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

# 1) source → clip → 9:16 (pipeline.py: yt-dlp 1080p, whisper, Gemini rank, crop)
if ! "$PY" "$SKILLS/pipeline.py" --url "$URL" --out "$WORK" --lang en --count 1 >"$WORK/pipe.log" 2>&1; then
  emit "pipeline failed for $URL (see /tmp log)"; exit 0
fi
# pipeline.py outputs clip.crop.mp4 (uncaptioned 9:16) + clip.final.mp4 (its own srt burn).
# We want OUR karaoke captions, so burn_captions runs on the UNCAPTIONED crop.
CLIP="$WORK/clip.crop.mp4"; [ -f "$CLIP" ] || CLIP="$WORK/clip.final.mp4"
[ -f "$CLIP" ] || CLIP=$(ls "$WORK"/*.mp4 2>/dev/null | grep -v raw | head -1)
[ -f "$CLIP" ] || { emit "no clip produced"; exit 0; }

# 2) burn EN karaoke captions (hook = first transcript line, optional)
HOOK=$("$PY" -c "import json;s=json.load(open('$WORK/transcript.json'));print((s[0].get('text','') if s else '')[:60])" 2>/dev/null || echo "")
"$PY" "$SKILLS/burn_captions.py" "$CLIP" "$WORK/EN.mp4" --hook "$HOOK" --model tiny --lang en >>"$WORK/pipe.log" 2>&1

# 3) verify GATE (9:16 / audio / non-black / 8-90s)
if ! bash "$SKILLS/verify_clip.sh" "$WORK/EN.mp4" >>"$WORK/pipe.log" 2>&1; then
  emit "clip FAILED verify_clip — not queued (source $URL)"; exit 0
fi

# 4) queue it (deterministic id from source) + caption sidecar
ID=$(printf '%s' "$URL" | sed 's#.*v=##; s#[^A-Za-z0-9_-]##g' | head -c 16)
DEST="$QUEUE/${ID}_EN.mp4"
cp "$WORK/EN.mp4" "$DEST"
cat > "$QUEUE/${ID}_EN.txt" <<CAP
${HOOK:-Money & AI clip} 💰

Follow for daily money + AI clips.

#money #investing #ai #wealth #finance #aiclips
CAP
emit "queued $(basename "$DEST") (verified, from $URL)"
