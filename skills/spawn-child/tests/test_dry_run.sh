#!/usr/bin/env bash
# Unit: spawn-child.sh --dry-run prints the daytona create invocation + cost estimate
# and never touches the Daytona API.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"
# daytona list --format json returns {items:[...]}; count .items, not top-level keys.
sandbox_count() { daytona list --format json 2>/dev/null | "$JQ" '(.items // []) | length'; }
BEFORE=$(sandbox_count)
OUT=$("$SKILL_DIR/scripts/spawn-child.sh" --dry-run anicca-test-dry)
AFTER=$(sandbox_count)
if [ "$BEFORE" != "$AFTER" ]; then
  echo "FAIL: sandbox count changed ($BEFORE -> $AFTER) on --dry-run"; exit 1
fi
echo "$OUT" | grep -qE '^DRY-RUN daytona create .*--name anicca-test-dry' || { echo "FAIL: missing create line"; exit 1; }
echo "$OUT" | grep -qE 'estimated cost: \$[0-9]+\.[0-9]{2}/hr' || { echo "FAIL: missing cost estimate"; exit 1; }
echo "PASS"
