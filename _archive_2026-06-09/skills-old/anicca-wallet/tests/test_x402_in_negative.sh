#!/usr/bin/env bash
# E2E NEGATIVE: forged receipt MUST return 402.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8403
LOG=$(mktemp); PID_FILE=$(mktemp)
cleanup() {
  if [ -s "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    wait "$(cat "$PID_FILE")" 2>/dev/null || true
  fi
  rm -f "$LOG" "$PID_FILE"
}
trap cleanup EXIT

python3 "$SKILL_DIR/scripts/x402_in_server.py" --port "$PORT" >"$LOG" 2>&1 &
echo $! > "$PID_FILE"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -o /dev/null --max-time 1 "http://127.0.0.1:$PORT/health" 2>/dev/null; then break; fi
  sleep 0.5
done

# (a) Unpaid → 402
RA=$(mktemp)
CODE_A=$(curl -sS -o "$RA" -w '%{http_code}' --max-time 3 "http://127.0.0.1:$PORT/paid")
[ "$CODE_A" = "402" ] || { echo "FAIL: unpaid returned $CODE_A"; cat "$RA"; exit 1; }

# (b) Forged → 402 with body {"error":"invalid receipt"}
FORGED=$(python3 "$SKILL_DIR/scripts/sign_demo_receipt.py" --route /paid --buyer-mode unsigned)
RB=$(mktemp)
CODE_B=$(curl -sS -o "$RB" -w '%{http_code}' --max-time 3 "http://127.0.0.1:$PORT/paid" -H "x-payment: $FORGED")
[ "$CODE_B" = "402" ] || { echo "FAIL: forged returned $CODE_B"; cat "$RB"; exit 1; }
/usr/bin/jq -e '.error == "invalid receipt"' "$RB" >/dev/null \
  || { echo "FAIL: forged body wrong"; cat "$RB"; exit 1; }

# (c) Self-signed → 200 (sanity)
SELF=$(python3 "$SKILL_DIR/scripts/sign_demo_receipt.py" --route /paid)
RC=$(mktemp)
CODE_C=$(curl -sS -o "$RC" -w '%{http_code}' --max-time 3 "http://127.0.0.1:$PORT/paid" -H "x-payment: $SELF")
[ "$CODE_C" = "200" ] || { echo "FAIL: self-signed returned $CODE_C"; cat "$RC"; exit 1; }

rm -f "$RA" "$RB" "$RC"
echo "PASS"
