#!/usr/bin/env bash
# verify_clip.sh — output verification GATE for a finished clip.
# Exit 0 = clip is postable; non-zero = BLOCK the post (the verification loop
# Dais wants baked into the skill — never post an unverified clip).
#
#   bash verify_clip.sh <clip.mp4> [--lang en|ja]
#
# Checks (all must pass):
#   1. video is 9:16 (portrait, ratio ~0.5625 ± 0.03)
#   2. audio stream exists AND is not near-silent (mean_volume > -50 dB)
#   3. duration in [8s, 90s] (short-form range)
#   4. a mid-clip frame is NOT black/blank (signalstats avg luminance)
#   5. resolution floor: width>=1080 AND height>=1920 (exact 1080x1920 post-fix)
#   6. video bitrate floor: >= 2500000 bps (stream bit_rate, format bit_rate fallback)
#
# Checks 5-6 added 2026-07-10 (quality self-heal incident: posted files measured
# 202x360 @ ~200kbps while 720p/1080p source formats existed for the same video id).
set -euo pipefail

CLIP="${1:?usage: verify_clip.sh <clip.mp4>}"
fail() { echo "[verify] FAIL: $1" >&2; exit 1; }

[ -f "$CLIP" ] || fail "file not found: $CLIP"

W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$CLIP" | head -1)
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$CLIP" | head -1)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CLIP" | head -1)
[ -n "${W:-}" ] && [ -n "${H:-}" ] || fail "no video stream"

# 1) aspect ratio ~9:16
RATIO=$(python3 -c "print(round($W/$H, 4))")
python3 -c "exit(0 if abs($W/$H - 0.5625) <= 0.03 else 1)" || fail "not 9:16 (got ${W}x${H}, ratio $RATIO)"

# 2) audio present + not silent
ACODEC=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$CLIP" || true)
[ -n "$ACODEC" ] || fail "no audio stream"
MEANVOL=$(ffmpeg -hide_banner -i "$CLIP" -af volumedetect -f null - 2>&1 | grep -oE 'mean_volume: -?[0-9.]+ dB' | grep -oE -- '-?[0-9.]+' | head -1)
[ -n "${MEANVOL:-}" ] || fail "could not read volume"
python3 -c "exit(0 if $MEANVOL > -50 else 1)" || fail "near-silent audio (mean_volume ${MEANVOL} dB)"

# 3) duration window
DUR=${DUR:-0}
python3 -c "exit(0 if 8 <= $DUR <= 90 else 1)" || fail "duration out of range (${DUR}s; want 8-90)"

# 4) mid frame not black (avg luma > 16 on 0-255)
MID=$(python3 -c "print(round($DUR/2, 2))")
TMPFR=$(mktemp -t verifyfr).png
ffmpeg -hide_banner -y -ss "$MID" -i "$CLIP" -vframes 1 "$TMPFR" >/dev/null 2>&1 || true
# mean grayscale luma via PIL (stdlib-free read); fallback to filesize heuristic
LUMA=$(python3 - "$TMPFR" <<'PY' 2>/dev/null || echo 0
import sys
try:
    from PIL import Image
    im=Image.open(sys.argv[1]).convert("L")
    px=list(im.getdata())
    print(round(sum(px)/len(px),1))
except Exception:
    print(0)
PY
)
rm -f "$TMPFR"
[ -n "${LUMA:-}" ] || LUMA=0
python3 -c "exit(0 if $LUMA > 16 else 1)" || fail "mid-frame appears black (YAVG ${LUMA})"

# 5) resolution floor (exact 1080x1920 is the post-fix target; floor check tolerates
# any future encode that meets or exceeds it)
python3 -c "exit(0 if ($W >= 1080 and $H >= 1920) else 1)" || fail "resolution below floor (got ${W}x${H}; want >=1080x1920)"

# 6) video bitrate floor >= 2.5Mbps. Prefer the per-stream video bit_rate; some
# containers/streamcopy paths omit it, so fall back to the container-level format
# bit_rate (includes audio, but is the best available signal rather than skipping
# the check).
VBITRATE=$(ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of csv=p=0 "$CLIP" | head -1)
if [ -z "${VBITRATE:-}" ] || [ "$VBITRATE" = "N/A" ]; then
  VBITRATE=$(ffprobe -v error -show_entries format=bit_rate -of csv=p=0 "$CLIP" | head -1)
fi
[ -n "${VBITRATE:-}" ] && [ "$VBITRATE" != "N/A" ] || fail "could not read video bitrate"
python3 -c "exit(0 if $VBITRATE >= 2500000 else 1)" || fail "bitrate below floor (${VBITRATE} bps; want >=2500000)"

echo "[verify] PASS — ${W}x${H} ${DUR}s audio=$ACODEC vol=${MEANVOL}dB luma=${LUMA} vbitrate=${VBITRATE}bps"
