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
http(){ local code; code=$(curl -s -m8 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null) || true; echo "${code:-000}"; }
# grep -q would SIGPIPE launchctl under pipefail → spurious STOPPED; capture instead
loop(){ [ -n "$(launchctl list 2>/dev/null | grep "$1")" ] && echo RUNNING || echo STOPPED; }

echo "════════════ ANICCA COLONY — LIVE SSOT ($(date -u +%Y-%m-%dT%H:%MZ)) ════════════"
echo ""
# a3cdd4 (~/.anicca, 0xB9dd, com.anicca.daemon) was listed here as a living citizen until
# 2026-07-16. It is not one: launchctl has no com.anicca.daemon, every plist is .disabled-*,
# and 48h external inflow is $0. Printing it made this script assert a citizen that does not
# run, which is exactly the kind of self-report that must never be mistaken for evidence.
# Retired by Dais on 2026-07-16. The colony is these three. See docs/STATUS.md.

echo "[1] franklin1       SELF-funded  (Franklin-Trading, Solana)   HOME=~/.blockrun"
echo "    sol    F5SY…hZ5T   SOL=$(sol F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T)  USDC=\$$(solusdc F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T)   loop(franklin-loop)=$(loop franklin-loop)"
echo "    x402   0x3EcCAD24…8749  Base USDC=\$$(erc20 $BASE $BUSDC 0x3EcCAD24794ca298D25378E9902A251322ea8749)   loop(x402-franklin1)=$(loop x402-franklin1)  url=:10001 public=$(http https://aniccanomac-mini-1.tail7a0ba4.ts.net:10001/)"
echo ""
echo "[2] franklin2       SELF-funded  (x402 seller)                HOME=~/.franklin2-home/.blockrun"
echo "    x402   0xe7747F…7ce9  Base USDC=\$$(erc20 $BASE $BUSDC 0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9)   loop(franklin2-loop)=$(loop franklin2-loop)  url=:10000"
echo ""
echo "[3] claude-p (me)   human-funded (this Claude → PM earner)     HOME=~/.anicca-founder"
echo "    x402   0x810f6d61…29c5  Base USDC=\$$(erc20 $BASE $BUSDC 0x810f6d61f7606deee2657d3083e150a222bc29c5)   loop(agent-economy-loop)=$(loop agent-economy-loop)"
# 0x904B50d2 holds the real funds (ERC-1167 proxy, no private key of its own -> cannot EIP-191 sign);
# telemetry is signed by a SEPARATE dedicated identity 0x02Bb... (~/.anicca-founder/state/telemetry-identity.json).
echo "    wallet 0x904B50d2…  pUSD=\$$(erc20 $POLY $PUSD 0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74)   loop(pm-earner)=$(loop pm-earner)  proxy-loop(founder-loop,0x810f)=$(loop founder-loop)"
DW=0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74
echo -n "    PM positions: "
curl -s -m8 "https://data-api.polymarket.com/positions?user=$DW&sizeThreshold=0.1" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);d=d if isinstance(d,list) else [];print(f'{len(d)} open, value \${sum(p.get(\"currentValue\",0) for p in d):.2f}, unrealized P&L \${sum(p.get(\"cashPnl\",0) for p in d):+.3f}')" 2>/dev/null
echo ""
echo "SELF-funded on Earth = 2 (franklin1, franklin2) | human-funded = 1 (claude-p)"
echo "openclaw + hermes = DELETED (not anicca-local). SSOT spec: docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md §19"
echo "════════════════════════════════════════════════════════════════════════════"
