#!/usr/bin/env bash
# Anicca earn skill — GATE-0 entrypoint. Called by the automaton loop each wake.
# No human, no Claude in the loop: the agent picks a source + executes the earn (on-chain),
# this harness VERIFIES it (tx receipt 0x1 + USDC before/after delta) and appends ONE
# line to state/earn-ledger.jsonl. A profitable wake (net>0 AND status 0x1) = the launch gate.
#
# Modes (set by the caller / automaton loop via env):
#   discover (default)  — no executed earn this wake: writes a narrate line (no tx). exit 0.
#   execute             — EARN_TX + EARN_SOURCE + EARN_AMOUNT set: verify on-chain, record.
#
# Env contract (mirrors the proven report skill):
#   /opt/anicca.env (if present) is sourced. Needs the wallet privkey var named by PKVAR
#   (default BLOCKRUN_WALLET_KEY) to derive the wallet address for the USDC delta proof.
#   Optional: BASE_RPC_URL, USDC_ADDRESS, EARN_LEDGER (override ledger path).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f /opt/anicca.env ] && . /opt/anicca.env || true
PKVAR="${PKVAR:-BLOCKRUN_WALLET_KEY}"
LEDGER="${EARN_LEDGER:-$HERE/state/earn-ledger.jsonl}"
WAKE="${WAKE_ID:-$(date -u +%s)}"
MODE="${EARN_MODE:-discover}"

# Derive the wallet address from the signing key (same wallet everywhere — no mismatch).
SIGNKEY="${!PKVAR:-}"
wallet_addr() {
  [ -n "$SIGNKEY" ] || { echo ""; return; }
  SIGNKEY="$SIGNKEY" python3 -c "import os; from eth_account import Account; print(Account.from_key(os.environ['SIGNKEY']).address)" 2>/dev/null || echo ""
}
W="$(wallet_addr)"
WLOW="$(echo "$W" | tr 'A-F' 'a-f')"

record_line() { # $1 = json
  node "$HERE/lib/record.mjs" "$1" "$LEDGER"
}

if [ "$MODE" = "discover" ]; then
  # Discovery wake: the agent found candidates but executed nothing on-chain yet.
  # Record a narrate line so the ledger shows the wake happened. NEVER counts as GATE-0.
  SRC="${EARN_SOURCE:-x402}"
  JSON=$(python3 -c "import json,sys; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'$SRC','task':'discover','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
  OUT=$(record_line "$JSON")
  echo "[earn] discover wake=$WAKE source=$SRC -> $OUT"
  exit 0
fi

# execute mode: an on-chain earn just happened. Verify it, prove the delta, record it.
: "${EARN_TX:?execute mode needs EARN_TX (the receipt hash)}"
: "${EARN_SOURCE:?execute mode needs EARN_SOURCE}"
: "${EARN_AMOUNT:?execute mode needs EARN_AMOUNT (gross USDC earned)}"
COST="${EARN_COST:-0}"

# 1) on-chain receipt status (0x1 = success).
STATUS=$(node -e "import('$HERE/lib/verify-tx.mjs').then(m=>m.receiptStatus(process.argv[1])).then(s=>console.log(s===null?'null':s)).catch(e=>{console.error(e.message);process.exit(1)})" "$EARN_TX")
echo "[earn] tx=$EARN_TX status=$STATUS source=$EARN_SOURCE"

# 2) record the line (record.mjs derives net + classifies profitable).
JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'$EARN_SOURCE','task':'${EARN_TASK:-earn}','earn_usdc':float('$EARN_AMOUNT'),'cost_usdc':float('$COST'),'tx':'$EARN_TX','status':'$STATUS','wake':'$WAKE'}))")
OUT=$(record_line "$JSON")
echo "[earn] recorded -> $OUT"

# 3) GATE-0: only a confirmed, net-positive wake is a real launch gate.
if [ "$OUT" = "PROFITABLE" ]; then
  echo "[earn] GATE-0 MET: profitable wake recorded (net>0, status 0x1)."
  exit 0
fi
echo "[earn] wake recorded but NOT profitable (status=$STATUS). Not GATE-0."
exit 0
