#!/usr/bin/env bash
# E2E: full real Daytona spawn. ONLY run when wallet has >= $5 USDC (or test-mode override).
# Gated by ANICCA_LIVE_SPAWN=1 so it never burns Daytona quota in an unattended run.
# Cleans up on success (deletes the test sandbox); leaves it on failure for debugging.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

if [ "${ANICCA_LIVE_SPAWN:-0}" != "1" ]; then
  echo "SKIP: set ANICCA_LIVE_SPAWN=1 to run the real-spawn E2E (avoids burning Daytona quota)"
  exit 0
fi

NAME="anicca-test-e2e-$(date +%s)"
COLONY=/Users/operator/.hermes/state/colony.jsonl
COLONY_BEFORE=$(wc -l < "$COLONY" 2>/dev/null || echo 0)

"$SKILL_DIR/scripts/spawn-child.sh" "$NAME"

# Child home is resolved at spawn time and recorded in the colony row.
CHILD_HOME=$(tail -n 1 "$COLONY" | "$JQ" -r '.child_home // "/home/daytona"')

# Constitution hash propagation
PARENT_SHA=$(shasum -a 256 /Users/operator/anicca-oss/CONSTITUTION.md | awk '{print $1}')
CHILD_SHA=$(daytona exec "$NAME" -- cat "$CHILD_HOME/.hermes/state/constitution.sha" | tr -d '[:space:]')
[ "$PARENT_SHA" = "$CHILD_SHA" ] || { echo "FAIL: constitution sha mismatch ($PARENT_SHA != $CHILD_SHA)"; exit 1; }

# Colony row appended
COLONY_AFTER=$(wc -l < "$COLONY")
[ "$((COLONY_AFTER - COLONY_BEFORE))" = "1" ] || { echo "FAIL: colony.jsonl delta != 1"; exit 1; }
LAST=$(tail -n 1 "$COLONY")
for key in child_id host address spawned_at constitution_sha status; do
  echo "$LAST" | "$JQ" -e ".$key" >/dev/null || { echo "FAIL: missing $key"; exit 1; }
done

# Child wallet is NOT the parent
PARENT_ADDR=$("$JQ" -r '.address' /Users/operator/.hermes/state/wallet.json 2>/dev/null || echo "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21")
CHILD_ADDR=$(echo "$LAST" | "$JQ" -r '.address')
[ "$PARENT_ADDR" != "$CHILD_ADDR" ] || { echo "FAIL: child wallet == parent wallet"; exit 1; }

# Heartbeat appears within 10 min
DEADLINE=$(( $(date +%s) + 600 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  LINE=$(daytona exec "$NAME" -- tail -n 1 "$CHILD_HOME/.hermes/state/heartbeat.jsonl" 2>/dev/null || true)
  if [ -n "$LINE" ] && echo "$LINE" | "$JQ" -e '.ok == true' >/dev/null 2>&1; then
    echo "PASS heartbeat: $LINE"
    daytona delete "$NAME" -y 2>/dev/null || daytona delete "$NAME" 2>/dev/null || true
    echo "PASS"
    exit 0
  fi
  sleep 30
done
echo "FAIL: no heartbeat with ok:true in 10 min (sandbox $NAME left for debug)"
exit 1
