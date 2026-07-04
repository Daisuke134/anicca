#!/usr/bin/env bash
# colony-status.sh — LIVE SSOT of the Anicca colony. Run this to see the truth NOW.
# Prints every instance: funding type, wallet, on-chain balance, loop status, P&L.
# This is the realtime answer to "who is on Earth + how much money".
set -uo pipefail
POLY=https://polygon-bor-rpc.publicnode.com
BASE=https://base-rpc.publicnode.com
SOLR=https://api.mainnet-beta.solana.com
PUSD=0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB
BUSDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
SOLUSDC=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

erc20(){ curl -s -m8 -X POST "$1" -H 'content-type: application/json' --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$2\",\"data\":\"0x70a08231000000000000000000000000${3:2}\"},\"latest\"]}" | python3 -c "import sys,json;r=json.load(sys.stdin).get('result','0x0');print('%.2f'%(int(r,16)/1e6) if r and r!='0x' else '0')" 2>/dev/null; }
sol(){ curl -s -m8 "$SOLR" -X POST -H 'content-type: application/json' --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getBalance\",\"params\":[\"$1\"]}" | python3 -c "import sys,json;print('%.3f'%(json.load(sys.stdin).get('result',{}).get('value',0)/1e9))" 2>/dev/null; }
solusdc(){ curl -s -m8 "$SOLR" -X POST -H 'content-type: application/json' --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenAccountsByOwner\",\"params\":[\"$1\",{\"mint\":\"$SOLUSDC\"},{\"encoding\":\"jsonParsed\"}]}" | python3 -c "import sys,json;v=json.load(sys.stdin).get('result',{}).get('value',[]);print('%.2f'%sum(float(a['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0) for a in v) if v else '0')" 2>/dev/null; }
# grep -q would SIGPIPE launchctl under pipefail → spurious STOPPED; capture instead
loop(){ [ -n "$(launchctl list 2>/dev/null | grep "$1")" ] && echo RUNNING || echo STOPPED; }

echo "════════════ ANICCA COLONY — LIVE SSOT ($(date -u +%Y-%m-%dT%H:%MZ)) ════════════"
echo ""
echo "[1] anicca-a3cdd4   SELF-funded  (automaton + ClawRouter)"
echo "    wallet 0xa3CDd4…C21  Base USDC=\$$(erc20 $BASE $BUSDC 0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21)   loop(founder-loop)=$(loop founder-loop)"
echo ""
echo "[2] Franklin        SELF-funded  (Franklin-Trading, Solana)"
echo "    wallet 8Fpqd…PCV9   SOL=$(sol 8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9)  USDC=\$$(solusdc 8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9)   loop(franklin-sol)=$(loop franklin-sol)"
echo ""
echo "[3] claude-p (me)   human-funded (this Claude → PM earner)"
echo "    wallet 0x904B50d2…  pUSD=\$$(erc20 $POLY $PUSD 0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74)   loop(pm-earner)=$(loop pm-earner)"
DW=0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74
echo -n "    PM positions: "
curl -s -m8 "https://data-api.polymarket.com/positions?user=$DW&sizeThreshold=0.1" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);d=d if isinstance(d,list) else [];print(f'{len(d)} open, value \${sum(p.get(\"currentValue\",0) for p in d):.2f}, unrealized P&L \${sum(p.get(\"cashPnl\",0) for p in d):+.3f}')" 2>/dev/null
echo ""
echo "SELF-funded on Earth = 2 (anicca-a3cdd4, Franklin) | human-funded = 1 (claude-p)"
echo "openclaw + hermes = DELETED (not anicca-local). SSOT spec: docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md §19"
echo "════════════════════════════════════════════════════════════════════════════"
