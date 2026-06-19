#!/usr/bin/env bash
# Anicca earn skill — GATE-0 entrypoint. Called by the automaton loop each wake.
# No human, no Claude in the loop: the agent picks a source + executes the earn (on-chain),
# this harness VERIFIES it (tx receipt 0x1 + USDC before/after delta) and appends ONE
# line to state/earn-ledger.jsonl. A profitable wake (net>0 AND status 0x1) = the launch gate.
#
# Modes (set by the caller / automaton loop via env):
#   discover (default)  — no executed earn this wake: writes a narrate line (no tx). exit 0.
#   execute             — perform/verify a real on-chain earn this wake and record it:
#     - EARN_STRATEGY=swap (default for the loop): run.sh ITSELF executes a real Uniswap V3
#       ETH->USDC swap (execute-swap.py), then records the receipt + real USDC delta. GATE-0.
#     - EARN_TX preset (externally-executed earn, e.g. x402): verify that tx, record it.
#
# Env contract (mirrors the proven report skill):
#   /opt/anicca.env (if present) is sourced. Needs the wallet privkey var named by PKVAR
#   (default BLOCKRUN_WALLET_KEY) to derive the wallet address for the USDC delta proof.
#   Optional: BASE_RPC_URL, USDC_ADDRESS, EARN_LEDGER (override ledger path).
#   Swap: EARN_SWAP_ETH (0.0003), EARN_SLIPPAGE_BPS (100), EARN_MIN_ETH_RESERVE (0.0005).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Env discovery: droplet ships /opt/anicca.env; local bodies keep the wallet key in the
# OpenClaw/clawd env. Source the first that exists so the loop finds the signing key anywhere.
# Allowlist ONLY the vars the earn path needs — never expose user-PII env (gmail/gcal/composio/
# google-login) to the earn process, or identity-guard.mjs (malice-guard) fails closed and HALTS.
# Reconciled against every env var read by run.sh + execute-0xwork.py (verified 2026-06-16).
EARN_ALLOW="BLOCKRUN_WALLET_KEY PKVAR OXWORK_PKVAR BASE_RPC_URL USDC_ADDRESS EARN_MODE EARN_STRATEGY EARN_TX EARN_SOURCE EARN_AMOUNT EARN_COST EARN_TASK EARN_LEDGER WAKE_ID OXWORK_API OXWORK_CAPS OXWORK_DELIVER OXWORK_POLL_SECS OXWORK_ANY_CATEGORY OXWORK_TASK_ID AUTO_CANCEL_USDC SUB_ID SELF_CANCEL_TOKEN ANICCA_API_BASE"
for ENVF in /opt/anicca.env "$HOME/.openclaw/.env" "$HOME/clawd/.env"; do
  [ -f "$ENVF" ] || continue
  while IFS= read -r kv; do
    k="${kv%%=*}"
    case " $EARN_ALLOW " in *" $k "*) export "$kv" ;; esac
  done < <(grep -E '^[A-Z_]+=' "$ENVF")
done
# Defense-in-depth: UNSET any inherited user-PII env (a contaminated parent may have exported it) so
# identity-guard.mjs (malice-guard) stays green regardless of how run.sh is invoked. Mirrors
# USER_PII_ENV_PATTERNS in skills/earn/lib/identity-guard.mjs.
for piivar in $(env | cut -d= -f1 | grep -iE 'GOOGLE_LOGIN|COMPOSIO|GCAL|GOOGLE_CALENDAR|GMAIL_REFRESH|GMAIL_TOKEN|USER.?GMAIL|TELEGRAM|^USER_|USER.?PHONE|USER.?CONTACT' 2>/dev/null); do
  unset "$piivar" 2>/dev/null || true
done
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

# distribute_ubi: after a PROFITABLE external wake, send a share of THIS wake's net to AI+human
# recipients (own wallet only). Fail-soft: never bricks the wake (the earn already succeeded).
# $1 = the SAME earn-line JSON we just recorded PROFITABLE.
distribute_ubi() {
  UBI_OUT=$(node "$HERE/distribute-ubi.mjs" "$1" 2>/dev/null || true)
  echo "[earn] ubi -> ${UBI_OUT:-noop}"
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

# execute mode.
# GATE-0 default = EXTERNAL revenue (0xwork). Swap is demoted to a non-gate runway fallback ONLY:
# a swap is net-zero asset rotation (Anicca's own ETH -> its own USDC), so the classifier
# (lib/ledger.mjs isProfitable) now rejects it. No EARN_STRATEGY value can mint GATE-0 from a swap.
STRATEGY="${EARN_STRATEGY:-yield}"

# --- strategy=0xwork: REAL EXTERNAL REVENUE (a poster's escrow pays USDC to our wallet) -------
if [ "$STRATEGY" = "0xwork" ] && [ -z "${EARN_TX:-}" ]; then
  RES=$(OXWORK_PKVAR="$PKVAR" PKVAR="$PKVAR" python3 "$HERE/execute-0xwork.py" 2>/dev/null)
  echo "[earn] 0xwork result: $RES"
  PAYTX=$(printf '%s' "$RES" | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get('payout_tx','') or '')" 2>/dev/null)
  TASKID=$(printf '%s' "$RES" | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get('task_id','') or 'claimed-awaiting-approval')" 2>/dev/null)
  if [ -z "$PAYTX" ]; then
    # No external payout this wake (no task / claimed+submitted awaiting poster approval).
    # Record NARRATE — never GATE-0 (no external:true). Honest residual.
    JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'0xwork','task':'$TASKID','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
    OUT=$(record_line "$JSON")
    echo "[earn] 0xwork narrate (no external payout yet) -> $OUT"
    exit 0
  fi
  # Assert the payout is an EXTERNAL inbound USDC transfer (from=taskPool) BEFORE recording GATE-0.
  RECEIPT=$(curl -s "${BASE_RPC_URL:-https://mainnet.base.org}" -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$PAYTX\"]}")
  EXT=$(printf '%s' "$RECEIPT" | node -e "let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',async()=>{try{const r=JSON.parse(s).result;const o=await import('$HERE/lib/oxwork.mjs');console.log(await o.isExternalPayout(r,'$WLOW'))}catch(e){console.log('false')}})")
  if [ "$EXT" != "true" ]; then
    echo "[earn] REJECT: $PAYTX is not an external 0xwork payout (from!=taskPool or no USDC transfer to us) — NOT GATE-0"
    exit 1
  fi
  STATUS=$(node -e "import('$HERE/lib/verify-tx.mjs').then(m=>m.receiptStatus('$PAYTX')).then(s=>console.log(s||'null')).catch(()=>console.log('null'))")
  BEFORE=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('before_usdc',0))" 2>/dev/null)
  AFTER=$(node -e "import('$HERE/lib/usdc.mjs').then(m=>m.usdcBalance('$WLOW')).then(b=>console.log(b)).catch(()=>console.log('$BEFORE'))")
  AMT=$(node -e "console.log(Math.max(0,($AFTER)-($BEFORE)))")
  # external:true is what unlocks isProfitable() — set ONLY here, after the assertion passed.
  JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'0xwork','task':'$TASKID','earn_usdc':float('$AMT'),'cost_usdc':0,'tx':'$PAYTX','status':'$STATUS','external':True,'wake':'$WAKE'}))")
  OUT=$(record_line "$JSON")
  echo "[earn] 0xwork recorded -> $OUT"
  if [ "$OUT" = "PROFITABLE" ]; then
    echo "[earn] GATE-0 MET: external revenue wake recorded (net>0, status 0x1, external inbound)."
    distribute_ubi "$JSON"
    exit 0
  fi
  echo "[earn] 0xwork wake recorded but NOT profitable (status=$STATUS). Not GATE-0."
  exit 0
fi

# --- strategy=x402: SAME-WAKE EXTERNAL fallback (sell Anicca's own output; instant settle) -----
# When 0xwork has no doable task this wake, sell a delivered artifact via x402 (04-earn.md
# "x402 sell own work"). x402 settles instantly — no poster-approval wait — so a wake can still
# close GATE-0. A payer streams USDC to our wallet for the artifact; the payout tx is an inbound
# USDC Transfer (from = payer, not self). EARN_STRATEGY=x402 -> execute-x402-sell.py prints
# {payout_tx,...}; the SAME isExternalPayout assertion + external:true gate applies before GATE-0.
# (execute-x402-sell.py is the next executor to land; until then 0xwork is the live external path.)

# --- strategy=swap: run.sh performs a NET-ZERO asset rotation (runway fallback, NEVER GATE-0) -
if [ "$STRATEGY" = "swap" ] && [ -z "${EARN_TX:-}" ]; then
  RES=$(PKVAR="$PKVAR" python3 "$HERE/execute-swap.py" 2>/dev/null)
  echo "[earn] swap result: $RES"
  # abort/error (e.g. ETH below gas reserve) -> degrade to a discover narrate line, never brick.
  ERR=$(printf '%s' "$RES" | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get('error') or d.get('abort') or '')" 2>/dev/null)
  if [ -n "$ERR" ]; then
    SRC="swap-eth-usdc"
    JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'$SRC','task':'swap-skipped:$ERR','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
    OUT=$(record_line "$JSON")
    echo "[earn] swap skipped ($ERR) -> recorded NARRATE -> $OUT"
    exit 0
  fi
  EARN_TX=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin)['tx'])")
  STATUS=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin)['status'])")
  EARN_AMOUNT=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin)['gross_usdc'])")
  COST=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin)['cost_usdc'])")
  EARN_SOURCE="swap-eth-usdc"
  EARN_TASK="${EARN_TASK:-eth->usdc liquidation for compute runway}"
  echo "[earn] tx=$EARN_TX status=$STATUS source=$EARN_SOURCE gross=$EARN_AMOUNT cost=$COST"
  JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'$EARN_SOURCE','task':'''$EARN_TASK''','earn_usdc':float('$EARN_AMOUNT'),'cost_usdc':float('$COST'),'tx':'$EARN_TX','status':'$STATUS','wake':'$WAKE'}))")
  OUT=$(record_line "$JSON")
  echo "[earn] recorded -> $OUT"
  # A swap line carries NO 'external' flag, so isProfitable() returns false by construction.
  # OUT is always NARRATE here: a swap is asset rotation (runway top-up), NEVER GATE-0.
  echo "[earn] swap wake recorded as NARRATE (asset rotation, not external revenue). Not GATE-0."
  exit 0
fi

# --- GAS FLOOR: never gas-stall. A wallet with USDC but zero native ETH cannot send ANY tx. Before
# the tx-doing legs, ensure a minimum ETH balance (self-restored by unwrapping a little WETH, or
# swapping a bit of USDC) so every Anicca can always act.
if [ "$STRATEGY" = "yield" ] && [ -z "${EARN_TX:-}" ]; then
  GRES=$(PKVAR="$PKVAR" node "$HERE/ensure-gas.mjs" 2>/dev/null)
  echo "[earn] gas check: $GRES"
fi

# --- INVESTING leg (3rd earning way): risk-managed blue-chip DCA into ETH, capped at a target % of
# investable capital (never the compute buffer, never leverage). Runs as part of the portfolio pass
# before yield, so each wake maintains: compute buffer (liquid) + blue-chip target + yield floor.
if [ "$STRATEGY" = "yield" ] && [ -z "${EARN_TX:-}" ]; then
  IRES=$(PKVAR="$PKVAR" node "$HERE/execute-invest.mjs" 2>/dev/null)
  echo "[earn] invest result: $IRES"
  IKIND=$(printf '%s' "$IRES" | python3 -c "import json,sys
try: print(json.load(sys.stdin).get('kind',''))
except Exception: print('')" 2>/dev/null)
  if [ "$IKIND" = "invest" ]; then
    ITX=$(printf '%s' "$IRES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('tx',''))" 2>/dev/null)
    IAMT=$(printf '%s' "$IRES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('bought_usd',0))" 2>/dev/null)
    IJSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'invest-eth-dca','task':'dca_buy_eth_${IAMT}','earn_usdc':0,'cost_usdc':0,'tx':'$ITX','kind':'invest','wake':'$WAKE'}))")
    record_line "$IJSON" >/dev/null 2>&1 || true
    echo "[earn] invest dca_buy \$$IAMT ETH (blue-chip leg) recorded"
  fi
  # fall through to the yield leg below (deploys the remaining surplus, keeps the compute buffer)
fi

# --- strategy=yield: GOAT earner — deploy idle USDC into DeFi yield (Aave v3) ---------------
# The agent's reliable, always-available earner. Net worth grows via accrual (aUSDC balance),
# withdrawable any time. NOT external revenue (kind:yield, external:false) -> never GATE-0;
# it is honest capital deployment at the market lending rate. When other earners have no live
# opportunity, the loop falls back here so a wake always does something productive.
if [ "$STRATEGY" = "yield" ] && [ -z "${EARN_TX:-}" ]; then
  RES=$(PKVAR="$PKVAR" node "$HERE/execute-yield.mjs" 2>/dev/null)
  echo "[earn] yield result: $RES"
  ABORT=$(printf '%s' "$RES" | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get('abort') or d.get('error') or '')" 2>/dev/null)
  if [ -n "$ABORT" ]; then
    JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'yield-aave-v3','task':'yield-skipped:$ABORT','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
    OUT=$(record_line "$JSON")
    echo "[earn] yield skipped ($ABORT) -> NARRATE -> $OUT"
    exit 0
  fi
  YTX=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('tx',''))")
  YSTATUS=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('status',''))")
  YAMT=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('deposited_usdc',0))")
  JSON=$(python3 -c "import json; print(json.dumps({'wallet':'${WLOW:-unknown}','source':'yield-aave-v3','task':'deploy idle USDC to Aave v3 yield','kind':'yield','deposited_usdc':float('$YAMT'),'earn_usdc':0,'cost_usdc':0,'tx':'$YTX','status':'$YSTATUS','external':False,'wake':'$WAKE'}))")
  OUT=$(record_line "$JSON")
  echo "[earn] yield deployed \$$YAMT to Aave v3 (tx=$YTX status=$YSTATUS) -> $OUT"
  exit 0
fi

# --- externally-executed earn (e.g. x402 inbound): an on-chain earn already happened ---------
: "${EARN_TX:?execute mode needs EARN_TX (the receipt hash) unless EARN_STRATEGY=swap}"
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
  distribute_ubi "$JSON"
  exit 0
fi
echo "[earn] wake recorded but NOT profitable (status=$STATUS). Not GATE-0."
exit 0
