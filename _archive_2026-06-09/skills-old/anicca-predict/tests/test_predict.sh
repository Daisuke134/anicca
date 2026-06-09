#!/usr/bin/env bash
# E2E (offline): predict.sh rejects a non-testable claim, records a testable one, and resolve.sh
# resolves expired claims via an injected evidence script (won) or marks unresolved (no script).
# Deadline expiry is forced with PREDICT_NOW_OVERRIDE so the test never waits in real time.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")/../scripts" && pwd)"
JQ=/usr/bin/jq

pass=0; fail=0
ok()  { echo "PASS: $1"; pass=$((pass+1)); }
bad() { echo "FAIL: $1"; fail=$((fail+1)); }

export STATE_DIR; STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/predict-e2e-XXXX")"
cleanup() { rm -rf "$STATE_DIR" 2>/dev/null || true; }
trap cleanup EXIT

PREDICTIONS="$STATE_DIR/predictions.jsonl"
POT="$STATE_DIR/predict-pot.jsonl"
EVID_DIR="$STATE_DIR/predict-evidence"

# ---- 1. Non-testable claim → exit 64, no row written.
bash "$SCRIPTS/predict.sh" "things will be good someday" "1" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 64 ] && [ ! -s "$PREDICTIONS" ]; then
  ok "non-testable claim rejected (exit 64, no row)"
else
  bad "non-testable claim not rejected (rc=$rc, file size=$(wc -c <"$PREDICTIONS" 2>/dev/null || echo 0))"
fi

# ---- 2. Testable claim → one open row with a 16-hex id.
CLAIM="earn-lancers gets first paid contract within 2h"
bash "$SCRIPTS/predict.sh" "$CLAIM" "\$1" >/dev/null 2>&1
PID="$("$JQ" -r 'select(.status=="open") | .prediction_id' "$PREDICTIONS" 2>/dev/null | head -1)"
if [ -n "$PID" ] && printf '%s' "$PID" | grep -Eq '^[0-9a-f]{16}$'; then
  ok "testable claim recorded as open with 16-hex id ($PID)"
else
  bad "testable claim not recorded properly (pid='$PID')"
  echo "--- predictions ---"; cat "$PREDICTIONS" 2>/dev/null
fi

# ---- 3. resolve.sh with an injected evidence script returning "won" → row flips to won + pot row.
mkdir -p "$EVID_DIR"
printf '#!/usr/bin/env bash\necho won\n' > "$EVID_DIR/$PID.sh"
chmod +x "$EVID_DIR/$PID.sh"
# Force "now" far in the future so the 2h deadline is expired.
PREDICT_NOW_OVERRIDE="$(( $(date +%s) + 100000 ))" bash "$SCRIPTS/resolve.sh" >/dev/null 2>&1 || true
if "$JQ" -e --arg p "$PID" 'select(.prediction_id==$p and .status=="won")' "$PREDICTIONS" >/dev/null 2>&1 \
   && [ -s "$POT" ] && "$JQ" -e --arg p "$PID" 'select(.prediction_id==$p and .payout=="mock")' "$POT" >/dev/null 2>&1; then
  ok "resolve flipped row to won + wrote a mock pot row"
else
  bad "resolve did not win/pot the prediction"
  echo "--- predictions ---"; cat "$PREDICTIONS" 2>/dev/null
  echo "--- pot ---"; cat "$POT" 2>/dev/null
fi

# ---- 4. Expired claim with NO evidence script → unresolved.
CLAIM2="x402 endpoint earns \$5 within 1d"
bash "$SCRIPTS/predict.sh" "$CLAIM2" "\$2" >/dev/null 2>&1
PID2="$("$JQ" -r 'select(.status=="open") | .prediction_id' "$PREDICTIONS" 2>/dev/null | head -1)"
PREDICT_NOW_OVERRIDE="$(( $(date +%s) + 200000 ))" bash "$SCRIPTS/resolve.sh" >/dev/null 2>&1 || true
if "$JQ" -e --arg p "$PID2" 'select(.prediction_id==$p and .status=="unresolved")' "$PREDICTIONS" >/dev/null 2>&1; then
  ok "expired claim with no evidence script → unresolved"
else
  bad "expired no-evidence claim not marked unresolved"
  echo "--- predictions ---"; cat "$PREDICTIONS" 2>/dev/null
fi

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
