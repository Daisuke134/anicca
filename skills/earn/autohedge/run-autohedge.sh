#!/usr/bin/env bash
# AutoHedge daily cycle → P&L email. Runs one bounded cycle on DeepSeek, emails result.
set -u
cd /Users/anicca/autohedge
set -a; . /Users/anicca/.openclaw/.env; set +a
AUTOHEDGE_GMAIL_ACCOUNT="${AUTOHEDGE_GMAIL_ACCOUNT:?AUTOHEDGE_GMAIL_ACCOUNT is required}"
AUTOHEDGE_REPORT_TO="${AUTOHEDGE_REPORT_TO:-$AUTOHEDGE_GMAIL_ACCOUNT}"
WALLET="tvTn7tisC5JWV81iDeFeLPcHapAamvXcyJVKia1TrNT"
USDC_MINT="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
TS=$(date +%Y%m%d-%H%M%S); LOG=/Users/anicca/autohedge/logs/cycle-$TS.log; mkdir -p /Users/anicca/autohedge/logs
bal(){ curl -s https://api.mainnet-beta.solana.com -X POST -H 'content-type: application/json' \
 -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenAccountsByOwner\",\"params\":[\"$WALLET\",{\"mint\":\"$USDC_MINT\"},{\"encoding\":\"jsonParsed\"}]}" 2>/dev/null \
 | python3 -c "import json,sys;v=json.load(sys.stdin)['result']['value'];print(v[0]['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] if v else 0)" 2>/dev/null; }
BEFORE=$(bal)
cat > .env <<EOF
JUPITER_API_KEY=${JUPITER_API_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
OPENAI_API_KEY=${DEEPSEEK_API_KEY}
WALLET_PRIVATE_KEY=${SOLANA_PRIVATE_KEY}
WORKSPACE_DIR=agent_workspace
EOF
export DEEPSEEK_API_KEY
timeout 600 .venv/bin/python -c "
from autohedge import AutoHedge
ts=AutoHedge(name='anicca-fund',description='Anicca crypto hedge fund on Solana')
print(ts.run(task='Analyze SOL on Solana short timeframe with live data. Risk-first: open a SMALL ~2 USDC long only if conviction is high, else stay flat. Execute via Jupiter if buying, else explain hold.'))
" >> "$LOG" 2>&1
rm -f .env
AFTER=$(bal)
DECISION=$(grep -oiE "stay flat|hold|buy|sell|executed" "$LOG" | tail -1)
PNL=$(python3 -c "print(round(${AFTER:-0}-${BEFORE:-0},4))" 2>/dev/null)
BODY="AutoHedge daily report ($TS JST)
Decision: ${DECISION:-n/a}
USDC before: ${BEFORE}  after: ${AFTER}
P&L today: ${PNL} USDC
Wallet: $WALLET
(log: $LOG)"
gog gmail send --account "$AUTOHEDGE_GMAIL_ACCOUNT" --to "$AUTOHEDGE_REPORT_TO" --subject "AutoHedge daily P&L: ${PNL} USDC (${DECISION:-hold})" --body "$BODY" 2>&1 | head -2
