#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="learning-$(date +%Y%m%d-%H%M%S)-$$"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
REPORT="$EVIDENCE/learning-decision.json"
SUMMARY="$EVIDENCE/summary.json"
TELEGRAM_OUTBOX="$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3"

mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$JOB_SEARCH_STATE_ROOT/logs"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"

TELEGRAM_ARGUMENTS=()
# Keep an explicit test/legacy executable override available, but production
# learning reports use the same private Bot API transport as daily and inbox.
if [[ "${JOB_SEARCH_OPENCLAW:-}" != "/opt/homebrew/bin/openclaw" && -n "${JOB_SEARCH_OPENCLAW:-}" ]]; then
  TELEGRAM_ARGUMENTS+=(--telegram-executable "$JOB_SEARCH_OPENCLAW")
fi

"$JOB_SEARCH_PYTHON" -m job_search_loop.learning run \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --strategy "$JOB_SEARCH_APP_ROOT/config/strategy.default.json" \
  --replay "$JOB_SEARCH_APP_ROOT/config/learning-replay.v1.json" \
  --report "$REPORT" \
  --outbox "$TELEGRAM_OUTBOX" \
  "${TELEGRAM_ARGUMENTS[@]}" \
  >"$SUMMARY"
chmod 600 "$REPORT" "$SUMMARY"
