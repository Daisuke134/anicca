#!/usr/bin/env bash
# Poll a HeyGen Video Agent project until the rendered mp4 is ready, then download it.
# Usage: render-download.sh <project_url_or_id> <out.mp4>
# CRITICAL: the finished video's download src is a <video> element src on files2.heygen.ai —
# it is NOT in the a11y/text snapshot. You MUST read it via JS (/evaluate), like this script does.
# (This was the gap that made unattended polling loop forever: the agent read the text snapshot,
#  which never shows the <video> src. 2026-05-23.)
set -uo pipefail
source "$(dirname "$0")/lib/camo.sh"
PROJ="$1"; OUT="$2"
case "$PROJ" in http*) URL="$PROJ";; *) URL="https://app.heygen.com/video-agent/$PROJ";; esac
TAB=$(camo_open "$URL"); sleep 8

for i in $(seq 1 36); do   # up to ~18 min (30s * 36)
  SRC=$(camo_eval "$TAB" '(()=>{const vs=[...document.querySelectorAll("video")].map(v=>v.src||v.currentSrc).filter(Boolean);const hit=vs.find(s=>/files2?\.heygen\.ai/.test(s)&&/attachment|\.mp4/.test(s))||vs.find(s=>/\.mp4|files2?\.heygen/.test(s));return hit||"";})()' 2>/dev/null | jq -r '.result // ""')
  if [ -n "$SRC" ] && [ "$SRC" != "null" ]; then
    echo "RENDER_READY (poll $i): downloading"
    curl -sSL "$SRC" -o "$OUT"
    if [ -s "$OUT" ] && ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null | grep -qE '[0-9]'; then
      echo "DOWNLOAD_OK $OUT ($(ffprobe -v error -show_entries stream=width,height -of csv=p=0:s=x "$OUT" 2>/dev/null | head -1))"
      camo_nav "$TAB" "about:blank" >/dev/null 2>&1; exit 0
    fi
    echo "downloaded but not a valid mp4, keep polling"
  fi
  sleep 30
done
echo "RENDER_TIMEOUT: no downloadable mp4 after 18 min on $URL"; exit 1
