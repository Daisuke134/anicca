#!/usr/bin/env bash
# Per-wake report: emails Dais 4 fields (AgentMail) + POSTs signed telemetry to aniccaai.com.
# Fired by the automaton loop's pre-sleep hook (running -> sleeping edge). No human in the loop.
set -u
. /opt/anicca.env
PKVAR=BLOCKRUN_WALLET_KEY                 # the wallet privkey var in /opt/anicca.env
SIGNKEY="${!PKVAR}"                       # indirect expansion: value of the var named by $PKVAR
# Derive the wallet address FROM the signing key so net worth, telemetry id, and signature all
# bind to the SAME wallet (a hardcoded address that disagreed would 401 signer_mismatch).
W=$(SIGNKEY="$SIGNKEY" python3 -c "import os; from eth_account import Account; print(Account.from_key(os.environ['SIGNKEY']).address)")
WLOW=$(echo "$W" | tr 'A-F' 'a-f'); WNO=${WLOW#0x}
LOG=/var/log/anicca-daemon.log
DID="${1:-$(grep -oE "\[TOOL\] [a-z_]+" "$LOG" 2>/dev/null | tail -5 | sed "s/\[TOOL\] //" | tr "\n" "," | sed "s/,$//")}"; DID="${DID:-monitoring}"
NEXT="${2:-continue earning + self-improve}"
rpc(){ curl -s --max-time 10 https://mainnet.base.org -X POST -H "Content-Type: application/json" --data "$1" | python3 -c "import json,sys;print(json.load(sys.stdin).get('result','0x0'))"; }
ETH=$(python3 -c "print(round(int('$(rpc "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"$W\",\"latest\"]}")',16)/1e18,6))")
USDC=$(python3 -c "print(round(int('$(rpc "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"data\":\"0x70a08231000000000000000000000000${WNO}\"},\"latest\"]}")',16)/1e6,4))")
DAY=$(date -u +%Y%m%d); BASE=/var/lib/anicca/baseline-$DAY; mkdir -p /var/lib/anicca; [ -f "$BASE" ] || echo "$USDC" > "$BASE"
REV=$(python3 -c "print(round($USDC - $(cat "$BASE"),4))")
# --- email (AgentMail) ---
curl -s --max-time 20 -X POST "https://api.agentmail.to/v0/inboxes/anicca-genesis@agentmail.to/messages/send" \
  -H "Authorization: Bearer $AGENTMAIL_API_KEY" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json;print(json.dumps({'to':['redacted@example.invalid','contact@aniccaai.com'],'subject':f'Anicca wake net \$$USDC','text':f'NET WORTH \$$USDC USDC (+$ETH ETH)\nREVENUE TODAY \$$REV\nDID $DID\nNEXT $NEXT'}))")" >/dev/null 2>&1
# --- telemetry: sign the VERBATIM message string and POST it as {message,signature} ---
# burn_day_usd/runway_days/status are PLACEHOLDERS until the earn/burn meter lands (spec25 R4).
TS=$(date -u +%s)
MSG=$(python3 -c "import json;print(json.dumps({'id':'$WLOW','ts':$TS,'host':'akash','geo':'US','model_live':'auto','model_tier':'free','net_worth_usd':$USDC,'revenue_mo_usd':$REV,'burn_day_usd':0,'runway_days':999,'status':'alive'},separators=(',',':')))")
SIG=$(MSG="$MSG" SIGNKEY="$SIGNKEY" python3 - <<'PY'
import os
from eth_account import Account
from eth_account.messages import encode_defunct
s = Account.sign_message(encode_defunct(text=os.environ["MSG"]), private_key=os.environ["SIGNKEY"]).signature.hex()
print(s if s.startswith("0x") else "0x"+s)        # ethers verifyMessage requires 0x prefix
PY
)
BODY=$(MSG="$MSG" SIG="$SIG" python3 -c "import json,os;print(json.dumps({'message':os.environ['MSG'],'signature':os.environ['SIG']}))")
curl -s --max-time 15 -X POST "https://aniccaai.com/.netlify/functions/telemetry" -H "Content-Type: application/json" \
  -d "$BODY" >/dev/null 2>&1
echo "report+telemetry $TS net=$USDC rev=$REV" >> /var/log/anicca-report.log
