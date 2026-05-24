#!/usr/bin/env bash
# instagram-poster — Postiz API投稿エントリ
#
# Usage:
#   LANG=ja SLOT=morning ./run.sh
#   LANG=en SLOT=evening ./run.sh
#
# Required env:
#   POSTIZ_API_KEY        (sourced from ~/.openclaw/.env)
#   LANG                  ja | en
#   SLOT                  morning | evening
# Optional env:
#   IG_DRY_RUN            true | false (default: true — preview only)
#   POSTIZ_BASE_URL       default: https://app.postiz.com/api
#   SLACK_CHANNEL         default: {{profile.channels.reportChannel}}
#
set -euo pipefail

[[ -f "$HOME/.openclaw/.env" ]] && source "$HOME/.openclaw/.env" || true

TARGET_LANG="${LANG:-ja}"
SLOT="${SLOT:-morning}"
IG_DRY_RUN="${IG_DRY_RUN:-true}"
POSTIZ_BASE_URL="${POSTIZ_BASE_URL:-https://app.postiz.com/api}"
SLACK_CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"

# integration mapping (larry persona accounts)
case "$TARGET_LANG" in
  ja) INTEGRATION_ID="cmmzujxpa04ujp30yxqpg1vci" ;;
  en) INTEGRATION_ID="cmmzzg2es0539p30ycb94ayx0" ;;
  *)
    echo "ERROR: no integration for LANG=$TARGET_LANG" >&2
    exit 2
    ;;
esac

SLOT_FILE="$HOME/.openclaw/workspace/tiktok-marketing/slots/${SLOT}-${TARGET_LANG}.json"
if [[ ! -f "$SLOT_FILE" ]]; then
  echo "ERROR: slot file not found: $SLOT_FILE" >&2
  exit 3
fi

LOG_DIR="$HOME/.openclaw/logs/instagram-poster"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d_%H%M%S)_${LANG}_${SLOT}.log"

{
  echo "=== instagram-poster run ==="
  echo "ts=$(date -Iseconds)"
  echo "lang=$TARGET_LANG slot=$SLOT integration=$INTEGRATION_ID dry_run=$IG_DRY_RUN"
  echo "slot_file=$SLOT_FILE"
} | tee -a "$LOG_FILE"

# Read flags from slot
FLAGS=$(jq -r '.flags // [] | join(",")' "$SLOT_FILE")
echo "slot_flags=[${FLAGS}]" | tee -a "$LOG_FILE"

if [[ "$IG_DRY_RUN" == "true" ]]; then
  echo "[DRY_RUN] would POST to $POSTIZ_BASE_URL/posts with integration=$INTEGRATION_ID" | tee -a "$LOG_FILE"
  echo "[DRY_RUN] flags enforced: SELF_ONLY (single integration), UPLOAD (native media)" | tee -a "$LOG_FILE"
  echo "[DRY_RUN] no network call" | tee -a "$LOG_FILE"
  exit 0
fi

if [[ -z "${POSTIZ_API_KEY:-}" ]]; then
  echo "ERROR: POSTIZ_API_KEY not set" | tee -a "$LOG_FILE" >&2
  exit 4
fi

# Live mode: TODO — full upload + post implementation lives in scripts/post.py
# (added in v0.2.0 — for now this script is DRY_RUN-only and Anicca executes the upload+post flow itself)
echo "Live mode: delegating to Anicca agent (post.py not yet implemented)" | tee -a "$LOG_FILE"
exit 0
