#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="daily-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
TELEGRAM_OUTBOX="$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3"

mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$JOB_SEARCH_STATE_ROOT/logs"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_BROWSER_OWNER_EVIDENCE="$EVIDENCE/browser-owner.json"
export JOB_SEARCH_CANDIDATE_QUEUE="$JOB_SEARCH_STATE_ROOT/candidate-queue.sqlite3"
"$JOB_SEARCH_PYTHON" -m job_search_loop.application_reporting deliver \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --outbox "$TELEGRAM_OUTBOX" \
  --media-root "$JOB_SEARCH_TELEGRAM_MEDIA" \
  --output "$EVIDENCE/resume-deliver-before.json"
JAPAN_DAY=$(TZ=Asia/Tokyo /bin/date +%F)
refresh_summary() {
  "$JOB_SEARCH_PYTHON" -m job_search_loop.summary \
    --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
    --output "$JOB_SEARCH_STATE_ROOT/summary.v2.json" \
    --day "$JAPAN_DAY"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.quota record \
    --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
    --day "$JAPAN_DAY" \
    --reason "hourly_pass_complete" \
    --output "$EVIDENCE/quota-deficit.json"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.daily_reporting deliver \
    --summary "$JOB_SEARCH_STATE_ROOT/summary.v2.json" \
    --outbox "$TELEGRAM_OUTBOX" \
    --output "$EVIDENCE/daily-pipeline-report.json"
}
SLOT_COUNT=$("$JOB_SEARCH_PYTHON" - "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" "$JAPAN_DAY" <<'PY'
import sys
from pathlib import Path

from job_search_loop.ledger import Ledger

ledger = Ledger(Path(sys.argv[1]))
try:
    print(ledger.daily_slot_count(sys.argv[2]))
finally:
    ledger.close()
PY
)
if [[ "$SLOT_COUNT" -ge "10" ]]; then
  "$JOB_SEARCH_JQ" -n \
    --arg status "daily_quota_reached" \
    --arg japan_day "$JAPAN_DAY" \
    --argjson slot_count "$SLOT_COUNT" \
    '{status:$status,japan_day:$japan_day,slot_count:$slot_count}' \
    >"$EVIDENCE/summary.json"
  chmod 600 "$EVIDENCE/summary.json"
  refresh_summary
  exit 0
fi
export JOB_SEARCH_RECOVERY_PLAN="$EVIDENCE/recovery-plan.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.recovery plan \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --day "$JAPAN_DAY" \
  --output "$JOB_SEARCH_RECOVERY_PLAN"
set +e
"$JOB_SEARCH_PYTHON" -m job_search_loop.official_ats_boards --refresh-only \
  --cache "$JOB_SEARCH_STATE_ROOT/official-ats-board-cache.v1.json" \
  >"$EVIDENCE/official-ats-refresh.json"
OFFICIAL_ATS_REFRESH_RC=$?
set -e
chmod 600 "$EVIDENCE/official-ats-refresh.json"
export ANICCA_BUDGET_REQUIRED=1
export ANICCA_LOOP_DAILY_TOKEN_BUDGET=1048576
export ANICCA_BUDGET_DAILY_SCOPE="job-search-daily"
export ANICCA_BUDGET_DAY_TZ="Asia/Tokyo"
export JOB_SEARCH_PREFILTER_RESULT="$EVIDENCE/prefilter-result.json"
JOB_SEARCH_PREFILTER_QUEUE="$EVIDENCE/prefilter-queue.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.prefilter \
  --recovery-plan "$JOB_SEARCH_RECOVERY_PLAN" \
  --framework-root "$JOB_SEARCH_FRAMEWORK_ROOT" \
  --queue-output "$JOB_SEARCH_PREFILTER_QUEUE" \
  --output "$JOB_SEARCH_PREFILTER_RESULT" \
  >"$EVIDENCE/prefilter-runner.json"
chmod 600 "$EVIDENCE/prefilter-runner.json"
chmod 600 "$JOB_SEARCH_PREFILTER_RESULT"
chmod 600 "$JOB_SEARCH_PREFILTER_QUEUE"
"$JOB_SEARCH_PYTHON" -m job_search_loop.candidate_queue discover-prefilter \
  --database "$JOB_SEARCH_CANDIDATE_QUEUE" \
  --input "$JOB_SEARCH_PREFILTER_QUEUE" \
  --output "$EVIDENCE/prefilter-candidate-receipt.json"
chmod 600 "$EVIDENCE/prefilter-candidate-receipt.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.ats_liveness sweep \
  --database "$JOB_SEARCH_CANDIDATE_QUEUE" \
  --evidence-dir "$EVIDENCE/ats-liveness" \
  --output "$EVIDENCE/ats-liveness-sweep.json" \
  --limit 100
export ANICCA_BUDGET_SCOPE_ID="job-search-daily:${RUN_ID}:terra-plan"
export ANICCA_PASS_TOKEN_BUDGET=65536
TERRA_PLAN_EVIDENCE="$EVIDENCE/terra-plan"
mkdir -p "$TERRA_PLAN_EVIDENCE"
chmod 700 "$TERRA_PLAN_EVIDENCE"
set +e
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class composition-agent \
  --prompt-stdin \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/terra-plan-result.v1.schema.json" \
  --evidence-dir "$TERRA_PLAN_EVIDENCE" \
  --task-label job-search-terra-plan \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  <"$JOB_SEARCH_APP_ROOT/prompts/terra-plan-pass.md" \
  >"$EVIDENCE/terra-plan-runner.json"
TERRA_PLAN_RC=$?
set -e
chmod 600 "$EVIDENCE/terra-plan-runner.json"
if [[ "$TERRA_PLAN_RC" -ne 0 ]]; then
  refresh_summary
  exit "$TERRA_PLAN_RC"
fi
TERRA_PLAN_RESULT_PATH=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/terra-plan-runner.json")
export JOB_SEARCH_TERRA_PLAN_RESULT="$EVIDENCE/terra-plan-result.json"
cp "$TERRA_PLAN_RESULT_PATH" "$JOB_SEARCH_TERRA_PLAN_RESULT"
chmod 600 "$JOB_SEARCH_TERRA_PLAN_RESULT"
export JOB_SEARCH_HIGH_MODE=dream
export ANICCA_BUDGET_SCOPE_ID="job-search-daily:${RUN_ID}:dream-high"
export ANICCA_PASS_TOKEN_BUDGET=65536
TERRA_HIGH_EVIDENCE="$EVIDENCE/terra-high"
mkdir -p "$TERRA_HIGH_EVIDENCE"
chmod 700 "$TERRA_HIGH_EVIDENCE"
set +e
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class job-search-terra-high \
  --escalation-reason "dream application dossier for deterministic dream candidates" \
  --prompt-file "$JOB_SEARCH_APP_ROOT/prompts/terra-high-pass.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/terra-high-result.v1.schema.json" \
  --evidence-dir "$TERRA_HIGH_EVIDENCE" \
  --task-label job-search-dream-high \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  >"$EVIDENCE/terra-high-runner.json"
TERRA_HIGH_RC=$?
set -e
chmod 600 "$EVIDENCE/terra-high-runner.json"
if [[ "$TERRA_HIGH_RC" -ne 0 ]]; then
  refresh_summary
  exit "$TERRA_HIGH_RC"
fi
TERRA_HIGH_RESULT_PATH=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/terra-high-runner.json")
export JOB_SEARCH_TERRA_HIGH_RESULT="$EVIDENCE/terra-high-result.json"
cp "$TERRA_HIGH_RESULT_PATH" "$JOB_SEARCH_TERRA_HIGH_RESULT"
chmod 600 "$JOB_SEARCH_TERRA_HIGH_RESULT"
JOB_SEARCH_BROWSER_FENCE="$JOB_SEARCH_STATE_ROOT/browser-fence"
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner acquire \
  --identity "job-search:dais" \
  --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
  --fence "$JOB_SEARCH_BROWSER_FENCE" \
  --holder-pid "$$"
JOB_SEARCH_BROWSER_LEASED=1
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner hold \
  --identity "job-search:dais" \
  --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
  --fence "$JOB_SEARCH_BROWSER_FENCE" \
  --holder-pid "$$" >/dev/null 2>&1 &
JOB_SEARCH_BROWSER_BEAT_PID=$!
TRAPEXIT() {
  if [[ -n "${JOB_SEARCH_BROWSER_BEAT_PID:-}" ]]; then
    kill "$JOB_SEARCH_BROWSER_BEAT_PID" >/dev/null 2>&1 || true
    wait "$JOB_SEARCH_BROWSER_BEAT_PID" >/dev/null 2>&1 || true
  fi
  if [[ "${JOB_SEARCH_BROWSER_LEASED:-0}" == "1" ]]; then
    "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner release \
      --identity "job-search:dais" \
      --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
      --fence "$JOB_SEARCH_BROWSER_FENCE" \
      --holder-pid "$$" >/dev/null 2>&1 || true
  fi
}
export ANICCA_BUDGET_SCOPE_ID="job-search-daily:${RUN_ID}:submit"
export ANICCA_PASS_TOKEN_BUDGET=98304
set +e
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class browser-lane-agent \
  --prompt-file "$JOB_SEARCH_APP_ROOT/prompts/daily-pass.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/pass-result.v1.schema.json" \
  --evidence-dir "$EVIDENCE" \
  --task-label job-search-daily \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT"
RUNNER_RC=$?
set -e
if [[ "$RUNNER_RC" -eq 0 ]]; then
  RESULT_PATH=$("$JOB_SEARCH_JQ" -er \
    '.result_path | select(type == "string" and length > 0)' \
    "$EVIDENCE/summary.json")
  set +e
  "$JOB_SEARCH_PYTHON" -m job_search_loop.candidate_queue validate-terminal \
    --database "$JOB_SEARCH_CANDIDATE_QUEUE" \
    --result "$RESULT_PATH" \
    --output "$EVIDENCE/candidate-terminal-receipt.json"
  TERMINAL_RC=$?
  set -e
  if [[ "$TERMINAL_RC" -ne 0 ]]; then
    RUNNER_RC=76
  fi
fi
PRIVACY_RC=0
PROVIDER_LOGS=(
  "$EVIDENCE"/attempt-*.stdout.log(N)
  "$TERRA_PLAN_EVIDENCE"/attempt-*.stdout.log(N)
  "$JOB_SEARCH_TERRA_PLAN_RESULT"
  "$TERRA_HIGH_EVIDENCE"/attempt-*.stdout.log(N)
  "$JOB_SEARCH_TERRA_HIGH_RESULT"
)
PRIVACY_INDEX=0
for PROVIDER_LOG in "${PROVIDER_LOGS[@]}"; do
  PRIVACY_INDEX=$((PRIVACY_INDEX + 1))
  "$JOB_SEARCH_PYTHON" -m job_search_loop.profile_privacy scan \
    --profile "$JOB_SEARCH_PROFILE" \
    --log "$PROVIDER_LOG" \
    --output "$EVIDENCE/profile-privacy-$PRIVACY_INDEX.json" \
    || PRIVACY_RC=$?
done
if [[ "$PRIVACY_RC" -ne 0 ]]; then
  RUNNER_RC=76
fi
if [[ "$RUNNER_RC" -ne 0 ]]; then
  refresh_summary
  if [[ "$RUNNER_RC" -eq 75 ]] \
    && "$JOB_SEARCH_JQ" -e '.status == "budget_blocked"' \
      "$EVIDENCE/summary.json" >/dev/null 2>&1; then
    exit 0
  fi
  exit "$RUNNER_RC"
fi
"$JOB_SEARCH_PYTHON" -m job_search_loop.application_reporting deliver \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --outbox "$TELEGRAM_OUTBOX" \
  --media-root "$JOB_SEARCH_TELEGRAM_MEDIA" \
  --output "$EVIDENCE/resume-deliver-after.json"
refresh_summary
