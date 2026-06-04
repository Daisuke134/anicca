#!/usr/bin/env bash
# E2E: signed EIP-3009 transferAuth recovers to the canonical Anicca wallet.
# NOTHING is broadcast.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

OUT=$(python3 "$SKILL_DIR/scripts/x402_out_dry_run.py" \
  --to 0x000000000000000000000000000000000000dEaD \
  --amount-usdc 0.01)

echo "$OUT" | /usr/bin/jq -e '.from == "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' >/dev/null \
  || { echo "FAIL: from != canonical"; echo "$OUT"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.to == "0x000000000000000000000000000000000000dEaD"' >/dev/null \
  || { echo "FAIL: to mismatch"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.value_atomic == 10000' >/dev/null \
  || { echo "FAIL: 0.01 USDC must encode as 10000 atomic (6 decimals)"; exit 1; }
echo "$OUT" | /usr/bin/jq -e '.recovered_signer == "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' >/dev/null \
  || { echo "FAIL: signature did not recover to canonical wallet"; echo "$OUT"; exit 1; }
# Signature must be 65 bytes = 130 hex chars + 0x prefix
echo "$OUT" | /usr/bin/jq -r .signature | /usr/bin/grep -Eq '^0x[a-fA-F0-9]{130}$' \
  || { echo "FAIL: signature is not 65 bytes hex"; exit 1; }
echo "PASS"
