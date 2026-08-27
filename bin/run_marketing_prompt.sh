#!/usr/bin/env bash
# Shared launchd boundary for bounded marketing jobs.
# The caller supplies content policy only; model/provider selection stays in agent-runner/config.json.
set -euo pipefail

LABEL=""
PROMPT_FILE=""
SCHEMA=""
LOOP="larry-marketing"
WORKDIR="/Users/anicca/.openclaw"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --label) LABEL="${2:-}"; shift 2 ;;
    --prompt) PROMPT_FILE="${2:-}"; shift 2 ;;
    --schema) SCHEMA="${2:-}"; shift 2 ;;
    --loop) LOOP="${2:-}"; shift 2 ;;
    --workdir) WORKDIR="${2:-}"; shift 2 ;;
    *) echo "run_marketing_prompt.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ "$LABEL" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "run_marketing_prompt.sh: invalid or missing --label" >&2
  exit 2
}
[[ "$LOOP" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "run_marketing_prompt.sh: invalid --loop" >&2
  exit 2
}
[ -f "$PROMPT_FILE" ] || {
  echo "run_marketing_prompt.sh: prompt not found: $PROMPT_FILE" >&2
  exit 2
}
[ -z "$SCHEMA" ] || [ -f "$SCHEMA" ] || {
  echo "run_marketing_prompt.sh: schema not found: $SCHEMA" >&2
  exit 2
}
[ -d "$WORKDIR" ] || {
  echo "run_marketing_prompt.sh: workdir not found: $WORKDIR" >&2
  exit 2
}

RUN_AGENT="${MARKETING_AGENT_WRAPPER:-/Users/anicca/anicca/skills/earn/marketing-engine/run_agent.sh}"
EVIDENCE_ROOT="${MARKETING_EVIDENCE_ROOT:-/Users/anicca/.local/state/anicca/evidence/marketing}"
[ -x "$RUN_AGENT" ] || {
  echo "run_marketing_prompt.sh: shared runner not executable: $RUN_AGENT" >&2
  exit 2
}

EVIDENCE_DIR="$EVIDENCE_ROOT/$LABEL/$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$EVIDENCE_DIR"

RUNNER_ARGS=(
  --task-class marketing-agent
  --evidence-dir "$EVIDENCE_DIR"
  --task-label "$LABEL"
  --loop "$LOOP"
  --workdir "$WORKDIR"
  --print-result
)
[ -z "$SCHEMA" ] || RUNNER_ARGS+=(--schema "$SCHEMA")

exec "$RUN_AGENT" "${RUNNER_ARGS[@]}" <"$PROMPT_FILE"
