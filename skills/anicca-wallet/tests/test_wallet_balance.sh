#!/usr/bin/env bash
# E2E: balance_watch.sh appends ONE well-formed JSON line and prints it.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${STATE_DIR:-/Users/anicca/.hermes/state}"
LOG="$STATE_DIR/wallet-balance.jsonl"
mkdir -p "$STATE_DIR"
BEFORE=$(wc -l < "$LOG" 2>/dev/null || echo 0)

OUT=$("$SKILL_DIR/scripts/balance_watch.sh")
AFTER=$(wc -l < "$LOG")

if [ $((AFTER - BEFORE)) -ne 1 ]; then
  echo "FAIL: expected +1 JSONL line, got $((AFTER - BEFORE))"; exit 1
fi

for key in address network usdc eth queried_at; do
  echo "$OUT" | /usr/bin/jq -e ".$key" >/dev/null || { echo "FAIL: stdout missing key $key"; exit 1; }
done

ADDR=$(echo "$OUT" | /usr/bin/jq -r .address)
if [ "$ADDR" != "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21" ]; then
  echo "FAIL: address $ADDR != canonical"; exit 1
fi
echo "PASS"
