#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/.." && pwd)"

OUTPUT=$(EARN_STRATEGY="x402_sell" ANICCA_HOME="/nonexistent_home" bash "$SKILL_DIR/run.sh" 2>&1 || true)

if echo "$OUTPUT" | grep -q "missing wallet identity\|no signing key resolved"; then
  echo "PASS: test_run_missing_wallet"
  exit 0
else
  echo "FAIL: expected missing wallet identity log in output, got:"
  echo "$OUTPUT"
  exit 1
fi
