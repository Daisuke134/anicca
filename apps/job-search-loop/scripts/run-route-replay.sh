#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="route-replay-$(date +%Y%m%d-%H%M%S)-$$"
EVIDENCE="${1:-$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID}"
SNAPSHOT="$JOB_SEARCH_APP_ROOT/config/model-route-replay.v1.json"
PROMPT="$JOB_SEARCH_APP_ROOT/prompts/model-route-replay.md"
SCHEMA="$JOB_SEARCH_APP_ROOT/schemas/model-route-replay-result.v1.schema.json"
mkdir -p "$EVIDENCE"
chmod 700 "$EVIDENCE"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_ROUTE_REPLAY_SNAPSHOT="$SNAPSHOT"
export JOB_SEARCH_ROUTE_REPLAY_SHA256=$("$JOB_SEARCH_PYTHON" - "$SNAPSHOT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
print(hashlib.sha256(canonical).hexdigest(), end="")
PY
)
export ANICCA_BUDGET_REQUIRED=1
export ANICCA_PASS_TOKEN_BUDGET=65536
export ANICCA_LOOP_DAILY_TOKEN_BUDGET=393216
export ANICCA_BUDGET_DAILY_SCOPE="job-search-route-replay:$RUN_ID"
export ANICCA_BUDGET_DAY_TZ="Asia/Tokyo"
export ANICCA_TOKEN_BUDGET_LEDGER="$EVIDENCE/token-budget.jsonl"
export ANICCA_USAGE_LEDGER="$EVIDENCE/usage.jsonl"

EVALUATOR_ARGS=(--snapshot "$SNAPSHOT")
for TRIAL in 1 2 3; do
  LUNA_EVIDENCE="$EVIDENCE/luna-$TRIAL"
  TERRA_EVIDENCE="$EVIDENCE/terra-$TRIAL"
  mkdir -p "$LUNA_EVIDENCE" "$TERRA_EVIDENCE"
  chmod 700 "$LUNA_EVIDENCE" "$TERRA_EVIDENCE"
  export ANICCA_BUDGET_SCOPE_ID="${RUN_ID}:luna:$TRIAL"
  "$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
    --task-class repeatable-agent --prompt-file "$PROMPT" --schema "$SCHEMA" \
    --evidence-dir "$LUNA_EVIDENCE" --task-label job-search-route-replay-luna \
    --loop job-search --workdir "$JOB_SEARCH_REPO_ROOT" \
    >"$EVIDENCE/luna-$TRIAL-runner.json"
  export ANICCA_BUDGET_SCOPE_ID="${RUN_ID}:terra:$TRIAL"
  "$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
    --task-class composition-agent --prompt-stdin --schema "$SCHEMA" \
    --evidence-dir "$TERRA_EVIDENCE" --task-label job-search-route-replay-terra \
    --loop job-search --workdir "$JOB_SEARCH_REPO_ROOT" \
    <"$PROMPT" >"$EVIDENCE/terra-$TRIAL-runner.json"
  LUNA_RESULT=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/luna-$TRIAL-runner.json")
  TERRA_RESULT=$("$JOB_SEARCH_JQ" -er '.result_path' "$EVIDENCE/terra-$TRIAL-runner.json")
  EVALUATOR_ARGS+=(
    --luna-result "$LUNA_RESULT" --luna-attempts "$LUNA_EVIDENCE/attempts.jsonl"
    --terra-result "$TERRA_RESULT" --terra-attempts "$TERRA_EVIDENCE/attempts.jsonl"
  )
done
"$JOB_SEARCH_PYTHON" -m job_search_loop.route_replay \
  "${EVALUATOR_ARGS[@]}" --output "$EVIDENCE/route-replay-receipt.json"
chmod 600 "$EVIDENCE"/*.json "$EVIDENCE"/*.jsonl(N) "$EVIDENCE"/*/*.json "$EVIDENCE"/*/*.jsonl
