#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
RUNTIME_PATHS_RC=0
set +e
source "$SCRIPT_DIR/runtime-paths.sh"
RUNTIME_PATHS_RC=$?
set -e
if [[ "$RUNTIME_PATHS_RC" -eq 0 ]] \
  && [[ -z "${AGENT_RUNNER_PROVIDER:-}" ]] \
  && [[ -f "$JOB_SEARCH_INSTALL_CONFIG" ]]; then
  RUNTIME_PATHS_RC=1
fi

RUN_ID="daily-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
export JOB_SEARCH_EVIDENCE_DIR="$EVIDENCE"
TELEGRAM_OUTBOX="$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3"
RESULT_PATH="$EVIDENCE/browser-worker-result.json"
FILL_CANARY_REQUEST="$JOB_SEARCH_STATE_ROOT/ashby-fill-canary-request.json"
FILL_CANARY_ACTIVE=0
REPORT_FAILURE_SENT=0
JOB_SEARCH_BROWSER_LEASED=0
JOB_SEARCH_BROWSER_BEAT_PID=""
MAIN_SHELL_PID=$$
MAIN_SHELL_SUBSHELL=$ZSH_SUBSHELL
SUMMARY_PATH="$EVIDENCE/summary.json"
export JOB_SEARCH_SUBMIT_ENABLED=1
export JOB_SEARCH_ASHBY_APPLY_MODULE="job_search_loop.ashby_apply"
export JOB_SEARCH_ASHBY_APPLY_RESULT="$EVIDENCE/ashby-apply-result.json"
if [[ -f "$FILL_CANARY_REQUEST" ]]; then
  FILL_CANARY_ACTIVE=1
  export JOB_SEARCH_NO_SUBMIT_CANARY=1
fi

export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_BROWSER_OWNER_EVIDENCE="$EVIDENCE/browser-owner.json"
export JOB_SEARCH_CANDIDATE_QUEUE="$JOB_SEARCH_STATE_ROOT/candidate-queue.sqlite3"
report_failure() {
  local kind="$1"
  if [[ "$REPORT_FAILURE_SENT" == "1" ]]; then
    return 0
  fi
  REPORT_FAILURE_SENT=1
  local message
  case "$kind" in
    limit)
      message="⏳ 今回は処理できる範囲に達したため、ここで安全に区切りました。正式な応募完了を確認できない求人は応募済みにしていません。次回の自動実行で、続きの確認を行います。"
      ;;
    verification)
      message="🛡️ 応募内容や証拠を確認できない状態になったため、安全のため停止しました。正式な応募完了を確認できない求人は応募済みにしていません。次回の自動実行で、確認できる状態から再開します。"
      ;;
    *)
      message="⚠️ 予期しない問題が起きたため、今回は停止しました。正式な応募完了を確認できない求人は応募済みにしていません。次の自動実行で状態を確認してから続けます。"
      ;;
  esac
  "$JOB_SEARCH_PYTHON" - "$TELEGRAM_OUTBOX" "$RUN_ID" "failure" "$message" <<'PY' || true
import sys
from pathlib import Path

from job_search_loop.telegram import send_once

send_once(
    database=Path(sys.argv[1]),
    event_key=f"job-search-progress:{sys.argv[2]}:{sys.argv[3]}",
    message=sys.argv[4],
)
PY
}
TRAPEXIT() {
  local exit_status=$?
  if [[ "$$" != "$MAIN_SHELL_PID" || "$ZSH_SUBSHELL" != "$MAIN_SHELL_SUBSHELL" ]]; then
    return "$exit_status"
  fi
  if [[ "$REPORT_FAILURE_SENT" != "1" && "$exit_status" -ne 0 ]]; then
    if [[ "$exit_status" -eq 76 ]]; then
      report_failure "verification"
    elif [[ "$exit_status" -eq 75 ]] \
      && [[ -f "$SUMMARY_PATH" ]] \
      && "$JOB_SEARCH_JQ" -e '.status == "budget_blocked"' \
        "$SUMMARY_PATH" >/dev/null 2>&1; then
      report_failure "limit"
    else
      report_failure "unexpected"
    fi
  fi
  if [[ -n "${JOB_SEARCH_BROWSER_BEAT_PID:-}" ]]; then
    kill "$JOB_SEARCH_BROWSER_BEAT_PID" >/dev/null 2>&1 || true
    wait "$JOB_SEARCH_BROWSER_BEAT_PID" >/dev/null 2>&1 || true
  fi
  if [[ "$JOB_SEARCH_BROWSER_LEASED" == "1" ]]; then
    "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_pages cleanup \
      --owner-receipt "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
      --ownership-receipt "$EVIDENCE/page-ownership.json" \
      --owned-page "$EVIDENCE/owned-page.json" \
      >"$EVIDENCE/page-cleanup.json" 2>/dev/null || true
    [[ ! -f "$EVIDENCE/page-cleanup.json" ]] || chmod 600 "$EVIDENCE/page-cleanup.json"
    "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner release \
      --identity "interactive:dais" \
      --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
      --fence "$JOB_SEARCH_BROWSER_FENCE" \
      --holder-pid "$$" >/dev/null 2>&1 || true
  fi
  return "$exit_status"
}
mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$JOB_SEARCH_STATE_ROOT/logs"
if [[ "$RUNTIME_PATHS_RC" -ne 0 ]]; then
  exit "$RUNTIME_PATHS_RC"
fi
ROUTE_FIXTURE_REQUEST="$JOB_SEARCH_STATE_ROOT/route-fixture-request.json"
ATS_SURFACE_CANARY_REQUEST="$JOB_SEARCH_STATE_ROOT/ats-surface-canary-request.json"
if [[ -f "$ROUTE_FIXTURE_REQUEST" ]]; then
  JOB_SEARCH_BROWSER_FENCE="$JOB_SEARCH_STATE_ROOT/browser-fence"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner acquire \
    --identity "interactive:dais" \
    --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --fence "$JOB_SEARCH_BROWSER_FENCE" \
    --holder-pid "$$"
  (
    TRAPEXIT() { :; }
    exec "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner hold \
      --identity "interactive:dais" \
      --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
      --fence "$JOB_SEARCH_BROWSER_FENCE" \
      --holder-pid "$$"
  ) >/dev/null 2>&1 &
  ROUTE_FIXTURE_BEAT_PID=$!
  set +e
  "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_worker route-fixture \
    --database "$JOB_SEARCH_CANDIDATE_QUEUE" \
    --owner-receipt "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --holder-pid "$$" \
    --run-id "$RUN_ID" \
    --lock "$JOB_SEARCH_STATE_ROOT/browser-worker.lock" \
    --worker-receipt "$EVIDENCE/browser-worker-receipt.json" \
    --evidence-dir "$EVIDENCE" \
    --route-fixture "$ROUTE_FIXTURE_REQUEST" \
    --output "$EVIDENCE/browser-worker-result.json" \
    >"$EVIDENCE/summary.json"
  ROUTE_FIXTURE_RC=$?
  set -e
  kill "$ROUTE_FIXTURE_BEAT_PID" >/dev/null 2>&1 || true
  wait "$ROUTE_FIXTURE_BEAT_PID" >/dev/null 2>&1 || true
  "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner release \
    --identity "interactive:dais" \
    --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --fence "$JOB_SEARCH_BROWSER_FENCE" \
    --holder-pid "$$" >/dev/null 2>&1 || true
  if [[ "$ROUTE_FIXTURE_RC" -eq 0 ]]; then
    mv "$ROUTE_FIXTURE_REQUEST" "$EVIDENCE/route-fixture-request.json"
    chmod 600 \
      "$EVIDENCE/route-fixture-request.json" \
      "$EVIDENCE/browser-worker-result.json" \
      "$EVIDENCE/browser-worker-receipt.json" \
      "$EVIDENCE/summary.json"
  fi
  exit "$ROUTE_FIXTURE_RC"
fi
if [[ -f "$ATS_SURFACE_CANARY_REQUEST" ]]; then
  JOB_SEARCH_BROWSER_FENCE="$JOB_SEARCH_STATE_ROOT/browser-fence"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner acquire \
    --identity "interactive:dais" \
    --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --fence "$JOB_SEARCH_BROWSER_FENCE" \
    --holder-pid "$$"
  (
    TRAPEXIT() { :; }
    exec "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner hold \
      --identity "interactive:dais" \
      --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
      --fence "$JOB_SEARCH_BROWSER_FENCE" \
      --holder-pid "$$"
  ) >/dev/null 2>&1 &
  ATS_CANARY_BEAT_PID=$!
  set +e
  "$JOB_SEARCH_PYTHON" -m job_search_loop.ats_surface_canary \
    --request "$ATS_SURFACE_CANARY_REQUEST" \
    --owner-receipt "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --profile "$JOB_SEARCH_PROFILE" \
    --materials-root "$JOB_SEARCH_MATERIALS_ROOT" \
    --evidence-dir "$EVIDENCE/ats-surface-canary" \
    --output "$EVIDENCE/ats-surface-canary-result.json" \
    >"$EVIDENCE/summary.json"
  ATS_CANARY_RC=$?
  set -e
  kill "$ATS_CANARY_BEAT_PID" >/dev/null 2>&1 || true
  wait "$ATS_CANARY_BEAT_PID" >/dev/null 2>&1 || true
  "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner release \
    --identity "interactive:dais" \
    --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --fence "$JOB_SEARCH_BROWSER_FENCE" \
    --holder-pid "$$" >/dev/null 2>&1 || true
  if [[ "$ATS_CANARY_RC" -eq 0 ]]; then
    mv "$ATS_SURFACE_CANARY_REQUEST" "$EVIDENCE/ats-surface-canary-request.json"
    chmod 600 "$EVIDENCE/ats-surface-canary-request.json" \
      "$EVIDENCE/ats-surface-canary-result.json" "$EVIDENCE/summary.json"
  fi
  exit "$ATS_CANARY_RC"
fi
"$JOB_SEARCH_PYTHON" -m job_search_loop.application_reporting deliver \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --outbox "$TELEGRAM_OUTBOX" \
  --media-root "$JOB_SEARCH_TELEGRAM_MEDIA" \
  --output "$EVIDENCE/resume-deliver-before.json"
JAPAN_DAY=$(TZ=Asia/Tokyo /bin/date +%F)
refresh_summary() {
  local deliver_report="${1:-1}"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.summary \
    --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
    --output "$JOB_SEARCH_STATE_ROOT/summary.v2.json" \
    --day "$JAPAN_DAY"
  if [[ "$deliver_report" == "1" ]]; then
    set +e
    "$JOB_SEARCH_PYTHON" -m job_search_loop.daily_reporting deliver \
      --summary "$JOB_SEARCH_STATE_ROOT/summary.v2.json" \
      --outbox "$TELEGRAM_OUTBOX" \
      --release-manifest "$JOB_SEARCH_REPO_ROOT/RELEASE.json" \
      --browser-result "$RESULT_PATH" \
      --output "$EVIDENCE/daily-pipeline-report.json"
    DAILY_REPORT_RC=$?
    set -e
    if [[ "$DAILY_REPORT_RC" -ne 0 ]]; then
      "$JOB_SEARCH_JQ" -n \
        --arg status "delivery_failed" \
        --argjson rc "$DAILY_REPORT_RC" \
        '{status:$status,rc:$rc}' \
        >"$EVIDENCE/daily-pipeline-report.json"
    fi
    chmod 600 "$EVIDENCE/daily-pipeline-report.json"
  fi
  return 0
}
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
  --input "$JOB_SEARCH_PREFILTER_RESULT" \
  --output "$EVIDENCE/prefilter-candidate-receipt.json"
chmod 600 "$EVIDENCE/prefilter-candidate-receipt.json"
mkdir -p "$EVIDENCE/ats-liveness"
chmod 700 "$EVIDENCE/ats-liveness"
"$JOB_SEARCH_JQ" -n '{status:"deferred_until_candidate_selection",checked_count:0}' \
  >"$EVIDENCE/ats-liveness-sweep.json"
chmod 600 "$EVIDENCE/ats-liveness-sweep.json"
ATS_CHECKED_COUNT=0
TERRA_PLAN_EVIDENCE="$EVIDENCE/terra-plan"
TERRA_HIGH_EVIDENCE="$EVIDENCE/terra-high"
mkdir -p "$TERRA_PLAN_EVIDENCE" "$TERRA_HIGH_EVIDENCE"
chmod 700 "$TERRA_PLAN_EVIDENCE" "$TERRA_HIGH_EVIDENCE"
export JOB_SEARCH_TERRA_PLAN_RESULT="$EVIDENCE/terra-plan-result.json"
export JOB_SEARCH_TERRA_HIGH_RESULT="$EVIDENCE/terra-high-result.json"
"$JOB_SEARCH_JQ" -n \
  '{status:"skipped_single_agent",dossiers:[],blocked:["owned_by_application_lane_agent"]}' \
  >"$JOB_SEARCH_TERRA_PLAN_RESULT"
"$JOB_SEARCH_JQ" -n \
  '{status:"skipped_single_agent",mode:"dream",dream_dossiers:[],hypothesis:null,blocked:["owned_by_application_lane_agent"]}' \
  >"$JOB_SEARCH_TERRA_HIGH_RESULT"
"$JOB_SEARCH_JQ" -n '{status:"skipped_single_agent"}' >"$EVIDENCE/terra-plan-runner.json"
"$JOB_SEARCH_JQ" -n '{status:"skipped_single_agent"}' >"$EVIDENCE/terra-high-runner.json"
chmod 600 "$JOB_SEARCH_TERRA_PLAN_RESULT" "$JOB_SEARCH_TERRA_HIGH_RESULT" \
  "$EVIDENCE/terra-plan-runner.json" "$EVIDENCE/terra-high-runner.json"
JOB_SEARCH_BROWSER_FENCE="$JOB_SEARCH_STATE_ROOT/browser-fence"
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner acquire \
  --identity "interactive:dais" \
  --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
  --fence "$JOB_SEARCH_BROWSER_FENCE" \
  --holder-pid "$$"
JOB_SEARCH_BROWSER_LEASED=1
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_pages open \
  --owner-receipt "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
  --ownership-receipt "$EVIDENCE/page-ownership.json" \
  --owned-page "$EVIDENCE/owned-page.json" \
  >"$EVIDENCE/page-open.json"
chmod 600 "$EVIDENCE/page-open.json"
(
  TRAPEXIT() { :; }
  exec "$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner hold \
    --identity "interactive:dais" \
    --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE" \
    --fence "$JOB_SEARCH_BROWSER_FENCE" \
    --holder-pid "$$"
) >/dev/null 2>&1 &
JOB_SEARCH_BROWSER_BEAT_PID=$!
set +e
/usr/bin/env -u JOB_SEARCH_PRIVATE_ENV \
  "$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class application-lane-agent \
  --prompt-file "$JOB_SEARCH_APP_ROOT/prompts/daily-apply-simple.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/pass-result.v1.schema.json" \
  --evidence-dir "$EVIDENCE" \
  --task-label job-search-daily \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  >"$EVIDENCE/summary.json"
RUNNER_RC=$?
set -e
if [[ "$FILL_CANARY_ACTIVE" == "1" ]]; then
  if [[ ! -f "$JOB_SEARCH_ASHBY_APPLY_RESULT" ]]; then
    RUNNER_RC=76
  else
    set +e
    "$JOB_SEARCH_PYTHON" -m job_search_loop.ashby_apply verify \
      --output "$JOB_SEARCH_ASHBY_APPLY_RESULT" \
      --profile "$JOB_SEARCH_PROFILE" \
      >"$EVIDENCE/ashby-fill-verification.json"
    FILL_VERIFY_RC=$?
    set -e
    chmod 600 "$EVIDENCE/ashby-fill-verification.json"
    if [[ "$FILL_VERIFY_RC" -ne 0 ]]; then
      RUNNER_RC=76
    fi
  fi
  mv "$FILL_CANARY_REQUEST" "$EVIDENCE/ashby-fill-canary-request.json"
  chmod 600 "$EVIDENCE/ashby-fill-canary-request.json"
fi
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
  set +e
  refresh_summary 0
  set -e
  if [[ "$RUNNER_RC" -eq 75 ]] \
    && "$JOB_SEARCH_JQ" -e '.status == "budget_blocked"' \
      "$EVIDENCE/summary.json" >/dev/null 2>&1; then
    report_failure "limit"
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
