#!/usr/bin/env bash
# Preflight: verify everything before generating a video.
# Exit code 0 if all OK. Non-zero if anything missing.
set -euo pipefail

LANG_ARG="${1:?usage: preflight.sh <en|jp>}"
case "$LANG_ARG" in en|jp) ;; *) echo "❌ unknown lang: $LANG_ARG"; exit 2 ;; esac

ROOT="$HOME/anicca-monk-factory"
[ -f "$ROOT/.env" ] || { echo "❌ missing $ROOT/.env"; exit 3; }

# Load env
set -a; . "$ROOT/.env"; set +a
export PATH="$HOME/.local/bin:$PATH"

FAIL=0
need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ missing bin: $1"; FAIL=1; }; }
need ffmpeg
need ffprobe
need curl
need python3
need magick
need heygen

# language-specific
CHAR_DIR="$ROOT/characters/$LANG_ARG"

if [ "$LANG_ARG" = "en" ]; then
  for k in HEYGEN_EN_AVATAR_LOOK_ID HEYGEN_EN_VOICE_ID POSTIZ_API_KEY POSTIZ_EN_TIKTOK_INTEGRATION; do
    eval v=\${$k:-}
    [ -z "$v" ] && { echo "❌ missing env: $k"; FAIL=1; }
  done
  # heygen wallet
  BAL=$(heygen user me get --human 2>/dev/null | awk '/Remaining Balance:/ {print $3}' | head -1)
  if [ -z "$BAL" ] || [ "${BAL%.*}" -lt 1 ] 2>/dev/null; then
    echo "❌ HeyGen wallet $BAL too low"; FAIL=1
  fi
fi

if [ "$LANG_ARG" = "jp" ]; then
  for k in OPENAI_API_KEY FAL_KEY POSTIZ_API_KEY POSTIZ_JP_TIKTOK_INTEGRATION ELEVENLABS_JP_VOICE_ID; do
    eval v=\${$k:-}
    [ -z "$v" ] && { echo "❌ missing env: $k"; FAIL=1; }
  done
  for i in 01 02 03 04 05; do
    [ -f "$CHAR_DIR/refs/test_pose_$i.jpg" ] || { echo "❌ missing $CHAR_DIR/refs/test_pose_$i.jpg"; FAIL=1; }
  done
fi

# Common
BANK="$ROOT/scripts/bank_$LANG_ARG.jsonl"
[ -s "$BANK" ] || { echo "❌ bank empty/missing: $BANK"; FAIL=1; }
mkdir -p "$ROOT/state" "$ROOT/renders" || { echo "❌ state/renders not writable"; FAIL=1; }

if [ $FAIL -eq 0 ]; then
  echo "✅ preflight ok ($LANG_ARG): $(wc -l < $BANK | tr -d ' ') scripts, $([ "$LANG_ARG" = "en" ] && echo "balance \$$BAL" || echo "5 refs")"
fi
exit $FAIL
