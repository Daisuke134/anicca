#!/usr/bin/env bash
# E2E test for the x402-cloud Worker. Verifies the real buyer-signed x402 flow.
#
# Usage:  BASE_URL=https://anicca-x402.<sub>.workers.dev ./test_x402_cloud_e2e.sh
#         (defaults to http://localhost:8788 for local `wrangler dev`)
#
# 3 graded scenarios + health + replay:
#   1. GET /paid no header                  → 402 + all x402 headers
#   2. self-signed receipt (signer != from) → 402 invalid_receipt (signer_not_from)
#   3. mock buyer-signed (signer == from)   → 200 ok, buyer == from
#   4. replay scenario-3 receipt            → 402 invalid_receipt (nonce_replay)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8788}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="${HERMES_STATE:-$HOME/.hermes/state}/.tmp-x402-e2e.$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
check() { # desc expected actual
  if [ "$2" = "$3" ]; then echo "PASS: $1 ($3)"; PASS=$((PASS+1));
  else echo "FAIL: $1 — expected $2 got $3"; FAIL=$((FAIL+1)); fi
}

# helper: GET with optional x-payment header, write body to file, echo status code
req() { # url [header]
  if [ -n "${2:-}" ]; then
    curl -s -o "$TMP/body" -w "%{http_code}" -H "x-payment: $2" "$1"
  else
    curl -s -o "$TMP/body" -w "%{http_code}" "$1"
  fi
}

echo "=== x402-cloud E2E against $BASE_URL ==="

# 0. health
code=$(req "$BASE_URL/health")
check "health 200" "200" "$code"

# 1. unpaid → 402 + headers
code=$(curl -s -o "$TMP/body" -D "$TMP/hdr" -w "%{http_code}" "$BASE_URL/paid")
check "unpaid 402" "402" "$code"
grep -qi "^WWW-Authenticate: x402" "$TMP/hdr" && { echo "PASS: WWW-Authenticate x402 header"; PASS=$((PASS+1)); } || { echo "FAIL: missing WWW-Authenticate x402"; FAIL=$((FAIL+1)); }
grep -qi "^x402-pay-to: 0xB9dd3B67921B354c656523d6851537988F31DD56" "$TMP/hdr" && { echo "PASS: x402-pay-to header"; PASS=$((PASS+1)); } || { echo "FAIL: missing x402-pay-to"; FAIL=$((FAIL+1)); }
grep -qi "^x402-asset: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" "$TMP/hdr" && { echo "PASS: x402-asset USDC header"; PASS=$((PASS+1)); } || { echo "FAIL: missing x402-asset"; FAIL=$((FAIL+1)); }

# 2. self-signed (signer != from) → 402 signer_not_from
SELF=$(python3 "$HERE/sign_buyer_auth.py" --mode selfsig)
code=$(req "$BASE_URL/paid" "$SELF")
check "self-signed rejected 402" "402" "$code"
reason=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('reason',''))" "$TMP/body")
check "self-signed reason signer_not_from" "signer_not_from" "$reason"

# 3. mock buyer-signed (signer == from != to) → 200 ok
BUYER=$(python3 "$HERE/sign_buyer_auth.py" --mode buyer)
# capture the from address from the receipt for buyer-match assertion
FROM=$(python3 -c "import base64,json,sys;print(json.loads(base64.b64decode(sys.argv[1])).get('from'))" "$BUYER")
code=$(req "$BASE_URL/paid" "$BUYER")
check "buyer-signed accepted 200" "200" "$code"
buyer=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('buyer','').lower())" "$TMP/body")
check "buyer == from" "$(echo "$FROM" | tr 'A-Z' 'a-z')" "$buyer"

# 4. replay same receipt → 402 nonce_replay (only meaningful with real KV; local KV persists per session)
code=$(req "$BASE_URL/paid" "$BUYER")
check "replay rejected 402" "402" "$code"
reason=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('reason',''))" "$TMP/body")
check "replay reason nonce_replay" "nonce_replay" "$reason"

echo "=== RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
