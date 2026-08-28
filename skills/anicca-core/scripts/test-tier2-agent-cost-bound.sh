#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HERE/tier2-agent-diagnose.sh"
RUNNER="$HERE/tier2-run-diagnosis.sh"
SCHEMA="$HERE/tier2-diagnosis.schema.json"
bash -n "$TARGET"
grep -q 'MAX_AGENT_DIAGNOSES_PER_PASS' "$TARGET"
grep -q 'TIER2_AGENT_RUNNER' "$TARGET"
grep -q 'LOG_CONTEXT_MAX_BYTES' "$TARGET"
grep -q 'EVIDENCE PACKET' "$TARGET"
grep -q 'Do not execute commands' "$TARGET"
test -x "$RUNNER"
test -f "$SCHEMA"
bash -n "$RUNNER"
grep -q 'runtime/agent-runner/agent_runner.py' "$RUNNER"
grep -q 'tier2-diagnosis.schema.json' "$RUNNER"
grep -q 'tier2-run-diagnosis.sh' "$TARGET"
if grep -q 'profitable-claude' "$TARGET" "$RUNNER" "$SCHEMA"; then
  echo "tier2 cost-bound contract failed: external checkout remains" >&2
  exit 1
fi
if grep -q 'openclaw agent --agent anicca' "$TARGET"; then
  echo "tier2 cost-bound contract failed: direct OpenClaw agent call remains" >&2
  exit 1
fi
echo "tier2 cost-bound contract: PASS"
