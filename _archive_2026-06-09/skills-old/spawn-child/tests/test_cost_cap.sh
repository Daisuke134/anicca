#!/usr/bin/env bash
# Unit: spawn-child.sh refuses to spawn when balance < $5 USDC.
# Uses __TEST_WALLET_OVERRIDE + ANICCA_TEST_MODE=1 (the test-only gate).
# Without ANICCA_TEST_MODE=1 the override is refused (exit 64) — production guard.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"
sandbox_count() { daytona list --format json 2>/dev/null | "$JQ" '(.items // []) | length'; }
BEFORE=$(sandbox_count)
set +e
OUT=$(ANICCA_TEST_MODE=1 __TEST_WALLET_OVERRIDE=2.50 \
      "$SKILL_DIR/scripts/spawn-child.sh" anicca-test-poor 2>&1)
CODE=$?
set -e
AFTER=$(sandbox_count)
[ "$CODE" = "75" ] || { echo "FAIL: expected exit 75, got $CODE"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -q 'cost cap: 2.50 USDC < 5 USDC required' || { echo "FAIL: missing cost-cap message"; echo "$OUT"; exit 1; }
[ "$BEFORE" = "$AFTER" ] || { echo "FAIL: sandbox count changed"; exit 1; }

# Negative test: same override WITHOUT ANICCA_TEST_MODE must be refused with 64.
set +e
__TEST_WALLET_OVERRIDE=100.00 "$SKILL_DIR/scripts/spawn-child.sh" anicca-test-prod-guard >/dev/null 2>&1
GUARD_CODE=$?
set -e
[ "$GUARD_CODE" = "64" ] || { echo "FAIL: production guard did not refuse stray override (got $GUARD_CODE)"; exit 1; }

echo "PASS"
