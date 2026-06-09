#!/usr/bin/env bash
# E2E:
#   1) Start the server in background.
#   2) GET /paid with NO header → expect HTTP 402 + the 4 mandatory x402 headers + pay_to JSON.
#   3) GET /paid with a signed x-payment header → expect HTTP 200 + recovered signer.
#   4) Tear down server, no orphans.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8403
LOG=$(mktemp)
PID_FILE=$(mktemp)

cleanup() {
  if [ -s "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    wait "$(cat "$PID_FILE")" 2>/dev/null || true
  fi
  rm -f "$LOG" "$PID_FILE"
}
trap cleanup EXIT

# Start server
python3 "$SKILL_DIR/scripts/x402_in_server.py" --port "$PORT" >"$LOG" 2>&1 &
echo $! > "$PID_FILE"

# Wait up to 5s for the listener
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -o /dev/null --max-time 1 "http://127.0.0.1:$PORT/health" 2>/dev/null; then break; fi
  sleep 0.5
done

# (1) No-payment request → 402
RESP=$(curl -sS -i --max-time 3 "http://127.0.0.1:$PORT/paid")
echo "$RESP" | head -1 | grep -q '402' || { echo "FAIL: expected 402 status line"; echo "$RESP"; exit 1; }
for h in 'WWW-Authenticate: x402' 'x402-network: base' \
         'x402-asset: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' \
         'x402-amount: 1000'; do
  echo "$RESP" | grep -qi "^$h" || { echo "FAIL: missing header: $h"; echo "$RESP"; exit 1; }
done
BODY=$(echo "$RESP" | awk 'f{print} /^\r?$/{f=1}')
echo "$BODY" | /usr/bin/jq -e '.pay_to == "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' >/dev/null \
  || { echo "FAIL: pay_to JSON mismatch"; echo "$BODY"; exit 1; }

# (2) Signed receipt → 200
RECEIPT=$(python3 "$SKILL_DIR/scripts/sign_demo_receipt.py" --route /paid)
RESP2=$(curl -sS -i --max-time 3 "http://127.0.0.1:$PORT/paid" -H "x-payment: $RECEIPT")
echo "$RESP2" | head -1 | grep -q '200' || { echo "FAIL: expected 200 with valid receipt"; echo "$RESP2"; exit 1; }
BODY2=$(echo "$RESP2" | awk 'f{print} /^\r?$/{f=1}')
echo "$BODY2" | /usr/bin/jq -e '.ok == true' >/dev/null \
  || { echo "FAIL: 200 body missing ok=true"; echo "$BODY2"; exit 1; }
echo "$BODY2" | /usr/bin/jq -e '.recovered == "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' >/dev/null \
  || { echo "FAIL: recovered signer != canonical"; echo "$BODY2"; exit 1; }

echo "PASS"
