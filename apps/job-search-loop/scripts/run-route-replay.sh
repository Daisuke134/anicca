#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="route-replay-$(date +%Y%m%d-%H%M%S)-$$"
EVIDENCE="${1:-$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID}"
SNAPSHOT="$JOB_SEARCH_APP_ROOT/config/model-route-replay.v1.json"
PROMPT="$JOB_SEARCH_APP_ROOT/prompts/model-route-replay.md"
SCHEMA="$JOB_SEARCH_APP_ROOT/schemas/model-route-replay-result.v1.schema.json"
mkdir -p "$EVIDENCE/luna" "$EVIDENCE/terra"
chmod 700 "$EVIDENCE" "$EVIDENCE/luna" "$EVIDENCE/terra"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_ROUTE_REPLAY_SNAPSHOT="$SNAPSHOT"
export ANICCA_BUDGET_REQUIRED=1
export ANICCA_PASS_TOKEN_BUDGET=65536
export ANICCA_LOOP_DAILY_TOKEN_BUDGET=131072
export ANICCA_BUDGET_DAILY_SCOPE="job-search-route-replay:$RUN_ID"
export ANICCA_BUDGET_DAY_TZ="Asia/Tokyo"
export ANICCA_TOKEN_BUDGET_LEDGER="$EVIDENCE/token-budget.jsonl"
export ANICCA_USAGE_LEDGER="$EVIDENCE/usage.jsonl"

export ANICCA_BUDGET_SCOPE_ID="${RUN_ID}:luna"
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class repeatable-agent \
  --prompt-file "$PROMPT" \
  --schema "$SCHEMA" \
  --evidence-dir "$EVIDENCE/luna" \
  --task-label job-search-route-replay-luna \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  >"$EVIDENCE/luna-runner.json"

export ANICCA_BUDGET_SCOPE_ID="${RUN_ID}:terra"
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class composition-agent \
  --prompt-stdin \
  --schema "$SCHEMA" \
  --evidence-dir "$EVIDENCE/terra" \
  --task-label job-search-route-replay-terra \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  <"$PROMPT" \
  >"$EVIDENCE/terra-runner.json"

LUNA_RESULT=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/luna-runner.json")
TERRA_RESULT=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/terra-runner.json")
"$JOB_SEARCH_PYTHON" -m job_search_loop.route_replay \
  --snapshot "$SNAPSHOT" \
  --luna-result "$LUNA_RESULT" \
  --luna-attempts "$EVIDENCE/luna/attempts.jsonl" \
  --terra-result "$TERRA_RESULT" \
  --terra-attempts "$EVIDENCE/terra/attempts.jsonl" \
  --output "$EVIDENCE/route-replay-receipt.json"
chmod 600 "$EVIDENCE"/*.json "$EVIDENCE"/*.jsonl(N) "$EVIDENCE"/*/*.json "$EVIDENCE"/*/*.jsonl
