#!/usr/bin/env bash
# youtube-shorts-poster — Postiz API投稿エントリ
#
# Usage:
#   LANG=ja ./run.sh
#   LANG=en ./run.sh
#
set -euo pipefail

[[ -f "$HOME/.openclaw/.env" ]] && source "$HOME/.openclaw/.env" || true

LANG="${LANG:-en}"
YT_DRY_RUN="${YT_DRY_RUN:-true}"
POSTIZ_BASE_URL="${POSTIZ_BASE_URL:-https://app.postiz.com/api}"
SLACK_CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"
SHORTS_MAX_SEC="${SHORTS_MAX_SEC:-60}"

case "$LANG" in
  en) INTEGRATION_ID="cmmzukbkw04ulp30yfvijrwio" ;;
  ja) INTEGRATION_ID="cmn1oukj9012nnq0yqhouc3ib" ;;
  *) INTEGRATION_ID="" ;;
esac
[[ -z "$INTEGRATION_ID" ]] && { echo "ERROR: no integration for LANG=$LANG" >&2; exit 2; }

DAY=$(date +%Y-%m-%d)
VIDEO="$HOME/.openclaw/workspace/youtube-shorts/${DAY}/${LANG}.mp4"

LOG_DIR="$HOME/.openclaw/logs/youtube-shorts-poster"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${DAY}_${LANG}.log"

{
  echo "=== youtube-shorts-poster run ==="
  echo "ts=$(date -Iseconds)"
  echo "lang=$LANG integration=$INTEGRATION_ID dry_run=$YT_DRY_RUN"
  echo "video=$VIDEO"
} | tee -a "$LOG_FILE"

if [[ ! -f "$VIDEO" ]]; then
  echo "WARNING: video not found at $VIDEO (upstream not ready)" | tee -a "$LOG_FILE"
  if [[ "$YT_DRY_RUN" != "true" ]]; then
    echo "ERROR: cannot post without video" | tee -a "$LOG_FILE" >&2
    exit 3
  fi
fi

if [[ "$YT_DRY_RUN" == "true" ]]; then
  echo "[DRY_RUN] would POST to $POSTIZ_BASE_URL/posts with integration=$INTEGRATION_ID" | tee -a "$LOG_FILE"
  echo "[DRY_RUN] flags enforced: SELF_ONLY+UPLOAD, type=YOUTUBE_SHORTS, max_duration=${SHORTS_MAX_SEC}s" | tee -a "$LOG_FILE"
  exit 0
fi

[[ -z "${POSTIZ_API_KEY:-}" ]] && { echo "ERROR: POSTIZ_API_KEY not set" >&2; exit 4; }
echo "Live mode: delegating to Anicca agent" | tee -a "$LOG_FILE"
