#!/usr/bin/env bash
# Provider-agnostic adapter for the TIER2 self-heal scanner.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
RUNNER="${AGENT_RUNNER_BIN:-$REPO_ROOT/runtime/agent-runner/agent_runner.py}"
SCHEMA="$HERE/tier2-diagnosis.schema.json"
EVIDENCE_ROOT="${TIER2_EVIDENCE_ROOT:-$HOME/.local/state/anicca/agent-runner-evidence/openclaw-tier2}"
WORKDIR="${TIER2_AGENT_WORKDIR:-$HOME/.openclaw}"
JOB_ID="${TIER2_JOB_ID:-unknown}"
SAFE_JOB_ID="$(printf '%s' "$JOB_ID" | tr -c 'A-Za-z0-9._-' '_')"
EVIDENCE_DIR="$EVIDENCE_ROOT/$SAFE_JOB_ID/$(date +%s)-$$"
PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/anicca-tier2-prompt.XXXXXX")"
trap 'rm -f "$PROMPT_FILE"' EXIT

[ -f "$RUNNER" ] || { echo "tier2 diagnosis runner missing: $RUNNER" >&2; exit 2; }
[ -f "$SCHEMA" ] || { echo "tier2 diagnosis schema missing: $SCHEMA" >&2; exit 2; }
mkdir -p "$EVIDENCE_DIR"
cat >"$PROMPT_FILE"
cat >>"$PROMPT_FILE" <<'EOF'

FINAL CONTRACT: return only JSON matching the supplied schema. Keep diagnosis and
action_taken factual and concise. Never claim an action without evidence.
EOF

RUNNER_LOG="$EVIDENCE_DIR/runner.log"
set +e
/usr/bin/python3 "$RUNNER" \
  --task-class diagnostic-agent \
  --prompt-file "$PROMPT_FILE" \
  --schema "$SCHEMA" \
  --evidence-dir "$EVIDENCE_DIR" \
  --task-label "openclaw-tier2-$SAFE_JOB_ID" \
  --loop openclaw-self-heal \
  --workdir "$WORKDIR" >"$RUNNER_LOG" 2>&1
RUNNER_RC=$?
set -e
if [ "$RUNNER_RC" -ne 0 ]; then
  tail -c 4000 "$RUNNER_LOG" >&2 2>/dev/null || true
  exit "$RUNNER_RC"
fi

/usr/bin/python3 - "$EVIDENCE_DIR/summary.json" <<'PY'
import json
import pathlib
import sys

summary_path = pathlib.Path(sys.argv[1])
summary = json.loads(summary_path.read_text(encoding="utf-8"))
if summary.get("status") != "success" or not summary.get("result_path"):
    raise SystemExit("tier2 diagnosis: successful runner has no fresh result")
result = json.loads(pathlib.Path(summary["result_path"]).read_text(encoding="utf-8"))
diagnosis = str(result.get("diagnosis", "")).strip()
action = str(result.get("action_taken", "")).strip()
confidence = str(result.get("confidence", "")).strip()
if not diagnosis or not action or confidence not in {"high", "medium", "low"}:
    raise SystemExit("tier2 diagnosis: malformed result contract")
print(f"DIAGNOSIS: {diagnosis}")
print(f"ACTION_TAKEN: {action}")
print(f"CONFIDENCE: {confidence}")
PY
