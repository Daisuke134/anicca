#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# threshold-check.sh — gate that decides whether anicca-001 may spawn a child.
#
# Per spec 13 § 6:
#   spawn_now = (wallet_usdc > 400) AND (uptime_days > 14) AND (lifeline == THRIVE)
#
# Reads inputs from ~/.openclaw/state/ and wallet RPC. Prints "ALLOW" or
# "BLOCK: <reason>" plus a JSON summary on stderr.

set -euo pipefail

THRESHOLD_USDC="${SPAWN_THRESHOLD_USDC:-400}"
THRESHOLD_DAYS="${SPAWN_THRESHOLD_DAYS:-14}"
EXPECTED_STATUS="${SPAWN_REQUIRE_STATUS:-THRIVE}"

WALLET="${ANICCA_WALLET_ADDR:-0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21}"
USDC_BASE="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# 1. wallet USDC via Base RPC eth_call (ERC-20 balanceOf)
SELECTOR="0x70a08231"
PADDED=$(printf '%064s' "${WALLET#0x}" | tr ' ' 0)
DATA="${SELECTOR}${PADDED}"

# shellcheck disable=SC2016
PAYLOAD=$(printf '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"%s","data":"%s"},"latest"]}' \
  "$USDC_BASE" "$DATA")

RESP=$(curl -fsS --max-time 8 \
  -H 'Content-Type: application/json' \
  -d "$PAYLOAD" \
  https://mainnet.base.org 2>/dev/null || echo '{}')

HEX=$(printf '%s' "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('result','0x0'))" 2>/dev/null || echo "0x0")
RAW_BAL=$(python3 -c "print(int('${HEX:-0x0}', 16))" 2>/dev/null || echo 0)
# USDC has 6 decimals
USDC_BAL=$(python3 -c "print(round(${RAW_BAL}/1e6, 6))")

# 2. uptime — earliest commit on this repo as proxy
GIT_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)
FIRST_COMMIT=$(git -C "$GIT_ROOT" log --reverse --format=%at 2>/dev/null | head -1 || echo 0)
NOW=$(date +%s)
if [[ "$FIRST_COMMIT" -gt 0 ]]; then
  UPTIME_DAYS=$(( (NOW - FIRST_COMMIT) / 86400 ))
else
  UPTIME_DAYS=0
fi

# 3. lifeline status — read from ~/.openclaw/state/lifeline.json if present
LIFELINE_FILE="$HOME/.openclaw/state/lifeline.json"
if [[ -f "$LIFELINE_FILE" ]]; then
  STATUS=$(python3 -c "import json; print(json.load(open('$LIFELINE_FILE')).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
else
  STATUS="UNKNOWN"
fi

# Decide
REASON=""
ALLOW=1
if (( $(echo "$USDC_BAL < $THRESHOLD_USDC" | bc -l 2>/dev/null || echo 1) )); then
  REASON="wallet_usdc=${USDC_BAL} < ${THRESHOLD_USDC}"
  ALLOW=0
elif [[ "$UPTIME_DAYS" -lt "$THRESHOLD_DAYS" ]]; then
  REASON="uptime_days=${UPTIME_DAYS} < ${THRESHOLD_DAYS}"
  ALLOW=0
elif [[ "$STATUS" != "$EXPECTED_STATUS" ]]; then
  REASON="lifeline=${STATUS} != ${EXPECTED_STATUS}"
  ALLOW=0
fi

SUMMARY=$(python3 -c "
import json
print(json.dumps({
  'wallet': '$WALLET',
  'wallet_usdc': $USDC_BAL,
  'threshold_usdc': $THRESHOLD_USDC,
  'uptime_days': $UPTIME_DAYS,
  'threshold_days': $THRESHOLD_DAYS,
  'lifeline_status': '$STATUS',
  'expected_status': '$EXPECTED_STATUS',
  'allow': bool($ALLOW),
  'reason': '$REASON'
}))
")
echo "$SUMMARY" >&2

if [[ "$ALLOW" -eq 1 ]]; then
  echo "ALLOW"
  exit 0
else
  echo "BLOCK: $REASON"
  exit 1
fi
