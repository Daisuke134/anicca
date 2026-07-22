#!/usr/bin/env bash
# Shared provider-agnostic boundary for revenue-loop judgment work.
# Consumers choose only a task class; provider/model routing lives in agent-runner/config.json.
set -euo pipefail

TASK_CLASS=""
EVIDENCE_DIR=""
TASK_LABEL=""
SCHEMA=""
WORKDIR="${AGENT_RUNNER_WORKDIR:-$HOME}"
PRINT_RESULT=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --task-class) TASK_CLASS="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --task-label) TASK_LABEL="${2:-}"; shift 2 ;;
    --schema) SCHEMA="${2:-}"; shift 2 ;;
    --workdir) WORKDIR="${2:-}"; shift 2 ;;
    --print-result) PRINT_RESULT=1; shift ;;
    *) echo "run_agent.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

case "$TASK_CLASS" in
  repeatable-agent|tool-agent|high-value-agent) ;;
  *) echo "run_agent.sh: invalid or missing --task-class" >&2; exit 2 ;;
esac
[ -n "$EVIDENCE_DIR" ] || { echo "run_agent.sh: missing --evidence-dir" >&2; exit 2; }
[ -n "$TASK_LABEL" ] || { echo "run_agent.sh: missing --task-label" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${AGENT_RUNNER_BIN:-$HOME/profitable-claude/skills/agent-runner/agent_runner.py}"
SCHEMA="${SCHEMA:-$SCRIPT_DIR/schemas/loop_pass.schema.json}"
[ -f "$RUNNER" ] || { echo "run_agent.sh: runner not found: $RUNNER" >&2; exit 2; }
[ -f "$SCHEMA" ] || { echo "run_agent.sh: schema not found: $SCHEMA" >&2; exit 2; }

mkdir -p "$EVIDENCE_DIR"
PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/marketing-agent-prompt.XXXXXX")"
trap 'rm -f "$PROMPT_FILE"' EXIT
cat >"$PROMPT_FILE"
cat >>"$PROMPT_FILE" <<'EOF'

FINAL CONTRACT: after completing the bounded work, return only JSON that satisfies the supplied output schema. Never claim an action without concrete evidence in the evidence array.
EOF

RUNNER_STDOUT="$EVIDENCE_DIR/runner.stdout.log"
set +e
/usr/bin/python3 "$RUNNER" \
  --task-class "$TASK_CLASS" \
  --prompt-file "$PROMPT_FILE" \
  --schema "$SCHEMA" \
  --evidence-dir "$EVIDENCE_DIR" \
  --task-label "$TASK_LABEL" \
  --workdir "$WORKDIR" >"$RUNNER_STDOUT"
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  cat "$RUNNER_STDOUT" >&2
  exit "$RC"
fi

if [ "$PRINT_RESULT" -eq 1 ]; then
  /usr/bin/python3 - "$EVIDENCE_DIR/summary.json" <<'PY'
import json, pathlib, sys
summary = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
result = summary.get("result_path")
if not result:
    raise SystemExit("run_agent.sh: successful summary has no result_path")
print(pathlib.Path(result).read_text(encoding="utf-8"), end="")
PY
else
  cat "$RUNNER_STDOUT"
fi
