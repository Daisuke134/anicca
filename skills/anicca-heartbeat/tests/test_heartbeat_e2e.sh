#!/usr/bin/env bash
# E2E: run heartbeat.sh once, assert it appends ONE well-formed JSON line.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE=/Users/anicca/.hermes/state/heartbeat.jsonl
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)
"$SKILL_DIR/scripts/heartbeat.sh"
AFTER=$(wc -l < "$STATE")
if [ $((AFTER - BEFORE)) -ne 1 ]; then
  echo "FAIL: expected +1 line, got $((AFTER - BEFORE))"; exit 1
fi
LAST=$(tail -n 1 "$STATE")
for key in ts ok fuel model constitution_sha; do
  echo "$LAST" | /usr/bin/jq -e ".$key" >/dev/null || { echo "FAIL: missing $key in $LAST"; exit 1; }
done
echo "$LAST" | /usr/bin/jq -e '.ok == true' >/dev/null || { echo "FAIL: ok != true"; exit 1; }
echo "PASS"
