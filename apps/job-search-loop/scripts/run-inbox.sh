#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="inbox-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
SEEN_STATE="$JOB_SEARCH_STATE_ROOT/inbox-seen.json"
CANDIDATES="$EVIDENCE/candidates.json"
PROMPT="$EVIDENCE/prompt.md"
PREP_DATABASE="$JOB_SEARCH_STATE_ROOT/interview-prep.sqlite3"
OUTBOX_DATABASE="$JOB_SEARCH_STATE_ROOT/ledger.sqlite3"
PREP_STATUS="$EVIDENCE/prep-status.json"
GMAIL_ACCOUNT="${JOB_SEARCH_GMAIL_ACCOUNT:-}"

if [[ -z "$GMAIL_ACCOUNT" ]]; then
  GMAIL_ACCOUNT=$("$JOB_SEARCH_JQ" -er \
    '.candidate.application_email // empty' "$JOB_SEARCH_PROFILE")
fi

mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$JOB_SEARCH_STATE_ROOT/logs"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
"$JOB_SEARCH_PYTHON" -m job_search_loop.interview_prep deliver \
  --database "$PREP_DATABASE" \
  --outbox "$OUTBOX_DATABASE" \
  --output "$EVIDENCE/prep-deliver-before.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.inbox scan \
  --account "$GMAIL_ACCOUNT" \
  --state "$SEEN_STATE" \
  --output "$CANDIDATES" \
  --prompt-base "$JOB_SEARCH_APP_ROOT/prompts/inbox-pass.md" \
  --prompt-output "$PROMPT" \
  --summary "$EVIDENCE/summary.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.interview_prep pending \
  --database "$PREP_DATABASE" \
  --output "$PREP_STATUS"
"$JOB_SEARCH_PYTHON" -m job_search_loop.interview_prep append-prompt \
  --database "$PREP_DATABASE" \
  --prompt "$PROMPT" \
  --profile "$JOB_SEARCH_PROFILE"
NEW_COUNT=$("$JOB_SEARCH_JQ" -r '.new_count' "$CANDIDATES")
PENDING_PREP_COUNT=$("$JOB_SEARCH_JQ" -r '.pending_count' "$PREP_STATUS")
if [[ "$NEW_COUNT" == "0" && "$PENDING_PREP_COUNT" == "0" ]]; then
  exit 0
fi
export ANICCA_BUDGET_REQUIRED=1
export ANICCA_BUDGET_SCOPE_ID="job-search-inbox:$RUN_ID"
export ANICCA_PASS_TOKEN_BUDGET=65536
export ANICCA_LOOP_DAILY_TOKEN_BUDGET=1048576
export ANICCA_BUDGET_DAILY_SCOPE="job-search-inbox"
export ANICCA_BUDGET_DAY_TZ="Asia/Tokyo"
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class composition-agent \
  --prompt-stdin \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/inbox-pass-result.v1.schema.json" \
  --evidence-dir "$EVIDENCE" \
  --task-label job-search-inbox \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  <"$PROMPT"
"$JOB_SEARCH_PYTHON" -m job_search_loop.inbox mark \
  --state "$SEEN_STATE" \
  --input "$CANDIDATES"
"$JOB_SEARCH_PYTHON" -m job_search_loop.interview_prep deliver \
  --database "$PREP_DATABASE" \
  --outbox "$OUTBOX_DATABASE" \
  --output "$EVIDENCE/prep-deliver-after.json"
