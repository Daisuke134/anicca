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
export JOB_SEARCH_HIGH_MODE=weekly
export JOB_SEARCH_LEARNING_REPORT="$REPORT"
export JOB_SEARCH_WEEKLY_HYPOTHESIS_RESULT="$EVIDENCE/weekly-hypothesis-result.json"
export ANICCA_BUDGET_REQUIRED=1
export ANICCA_BUDGET_SCOPE_ID="job-search-learning:${RUN_ID}:weekly-high"
export ANICCA_PASS_TOKEN_BUDGET=65536
export ANICCA_LOOP_DAILY_TOKEN_BUDGET=131072
export ANICCA_BUDGET_DAILY_SCOPE="job-search-learning"
export ANICCA_BUDGET_DAY_TZ="Asia/Tokyo"
HIGH_EVIDENCE="$EVIDENCE/terra-high"
mkdir -p "$HIGH_EVIDENCE"
chmod 700 "$HIGH_EVIDENCE"
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class job-search-terra-high \
  --escalation-reason "one bounded weekly job-funnel improvement hypothesis" \
  --prompt-file "$JOB_SEARCH_APP_ROOT/prompts/terra-high-pass.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/terra-high-result.v1.schema.json" \
  --evidence-dir "$HIGH_EVIDENCE" \
  --task-label job-search-weekly-hypothesis \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  >"$EVIDENCE/terra-high-runner.json"
chmod 600 "$EVIDENCE/terra-high-runner.json"
HIGH_RESULT_PATH=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/terra-high-runner.json")
cp "$HIGH_RESULT_PATH" "$JOB_SEARCH_WEEKLY_HYPOTHESIS_RESULT"
chmod 600 "$JOB_SEARCH_WEEKLY_HYPOTHESIS_RESULT"
