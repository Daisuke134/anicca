#!/usr/bin/env bash
set -euo pipefail

TARGET="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tier2-agent-diagnose.sh"
bash -n "$TARGET"
grep -q 'MAX_AGENT_DIAGNOSES_PER_PASS' "$TARGET"
grep -q 'TIER2_AGENT_RUNNER' "$TARGET"
grep -q 'LOG_CONTEXT_MAX_BYTES' "$TARGET"
grep -q 'EVIDENCE PACKET' "$TARGET"
grep -q 'Do not execute commands' "$TARGET"
if grep -q 'openclaw agent --agent anicca' "$TARGET"; then
  echo "tier2 cost-bound contract failed: direct OpenClaw agent call remains" >&2
  exit 1
fi
echo "tier2 cost-bound contract: PASS"
