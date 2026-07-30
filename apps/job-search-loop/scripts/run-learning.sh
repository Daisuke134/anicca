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

"$JOB_SEARCH_PYTHON" -m job_search_loop.learning run \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --strategy "$JOB_SEARCH_APP_ROOT/config/strategy.default.json" \
  --replay "$JOB_SEARCH_APP_ROOT/config/learning-replay.v1.json" \
  --report "$REPORT" \
  --outbox "$TELEGRAM_OUTBOX" \
  --telegram-executable "$JOB_SEARCH_OPENCLAW" \
  >"$SUMMARY"
chmod 600 "$REPORT" "$SUMMARY"
