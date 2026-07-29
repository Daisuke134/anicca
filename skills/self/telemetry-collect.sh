#!/usr/bin/env bash
# telemetry-collect.sh — writes ONE machine-readable state/telemetry.json per Anicca-colony instance,
# straight into that instance's own body directory (never into a shared/central location). This is the
# #25 TELEM first step: make each instance's wallet balance + P&L + loop status readable on disk so a
# (Dais-owned) dashboard-sync can pick it up later. Read-only: every balance comes from PUBLIC RPC/API
# reads (same calls as skills/self/colony-status.sh) — NO private key is ever read, decrypted, or logged.
#
# Instances covered (per docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md §19):
#   1. anicca-a3cdd4 (automaton+ClawRouter, SELF-funded)  -> ~/.automaton/state/telemetry.json
#   2. Franklin      (Franklin-Trading, SELF-funded)      -> ~/.blockrun/state/telemetry.json
#   3. claude-p      (PM earner, human-funded)            -> ~/.anicca-founder/state/telemetry.json
#
# Usage: bash telemetry-collect.sh   (safe to run manually any number of times; each run overwrites its
# own instance's telemetry.json with a fresh snapshot). NOT wired into launchd/cron by this script —
# scheduling is a separate, reviewed step.
set -uo pipefail

POLY=https://polygon-bor-rpc.publicnode.com
BASE=https://base-rpc.publicnode.com
SOLR=https://api.mainnet-beta.solana.com
PUSD=0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB
BUSDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
SOLUSDC=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

A3CDD4_ADDR=0xB9dd3B67921B354c656523d6851537988F31DD56
FRANKLIN_ADDR=F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T
CLAUDEP_ADDR=0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74

erc20() { curl -s -m8 -X POST "$1" -H 'content-type: application/json' \
  --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$2\",\"data\":\"0x70a08231000000000000000000000000${3:2}\"},\"latest\"]}" \
  | python3 -c "import sys,json;r=json.load(sys.stdin).get('result','0x0');print('%.6f'%(int(r,16)/1e6) if r and r!='0x' else '0')" 2>/dev/null; }
sol() { curl -s -m8 "$SOLR" -X POST -H 'content-type: application/json' \
  --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getBalance\",\"params\":[\"$1\"]}" \
  | python3 -c "import sys,json;print('%.6f'%(json.load(sys.stdin).get('result',{}).get('value',0)/1e9))" 2>/dev/null; }
solusdc() { curl -s -m8 "$SOLR" -X POST -H 'content-type: application/json' \
  --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenAccountsByOwner\",\"params\":[\"$1\",{\"mint\":\"$SOLUSDC\"},{\"encoding\":\"jsonParsed\"}]}" \
  | python3 -c "import sys,json;v=json.load(sys.stdin).get('result',{}).get('value',[]);print('%.6f'%sum(float(a['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0) for a in v) if v else '0')" 2>/dev/null; }
# grep -q would SIGPIPE launchctl under pipefail -> spurious STOPPED; capture instead (same fix as colony-status.sh)
loop_status() { [ -n "$(launchctl list 2>/dev/null | grep "$1")" ] && echo RUNNING || echo STOPPED; }
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
now_epoch() { date -u +%s; }

pm_positions_json() {
  # Polymarket open positions + unrealized P&L for the given proxy wallet (public data-api, no auth).
  curl -s -m8 "https://data-api.polymarket.com/positions?user=$1&sizeThreshold=0.1" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = []
if not isinstance(d, list):
    d = []
open_count = len(d)
value = sum(p.get('currentValue', 0) or 0 for p in d)
upnl = sum(p.get('cashPnl', 0) or 0 for p in d)
print(json.dumps({'open_positions': open_count, 'value_usd': round(value, 6), 'unrealized_pnl_usd': round(upnl, 6)}))
" 2>/dev/null
}

# ---- 1. anicca-a3cdd4 (automaton) --------------------------------------------------------------
# NOTE (spec §25 correction, adversary FIND 2026-07-05): anicca-a3cdd4's REAL launchd loop is
# com.anicca.daemon (body ~/.anicca) -- "ai.anicca.founder-loop" is a SEPARATE, unrelated job
# (claude-p's proxy body, wallet 0x810f). This script previously reported the wrong loop's status.
A3_BAL=$(erc20 "$BASE" "$BUSDC" "$A3CDD4_ADDR")
A3_LOOP=$(loop_status anicca.daemon)
A3_OUT=$HOME/.automaton/state/telemetry.json
mkdir -p "$(dirname "$A3_OUT")"
python3 -c "
import json
doc = {
    'instance': 'anicca-a3cdd4',
    'type': 'SELF-funded',
    'wallet': {'address': '$A3CDD4_ADDR', 'chain': 'base', 'asset': 'USDC'},
    'balance_usd': float('$A3_BAL' or 0),
    'pnl': None,
    'loop': {'name': 'com.anicca.daemon', 'launchd_label': 'com.anicca.daemon', 'status': '$A3_LOOP'},
    'generated_at': '$(now_iso)',
    'generated_at_epoch': $(now_epoch),
    'source': 'public RPC read (base-rpc.publicnode.com), no private key accessed'
}
open('$A3_OUT', 'w').write(json.dumps(doc, indent=2) + '\n')
"
echo "wrote $A3_OUT"

# ---- 2. Franklin (Franklin-Trading, Solana) ----------------------------------------------------
FR_SOL=$(sol "$FRANKLIN_ADDR")
FR_USDC=$(solusdc "$FRANKLIN_ADDR")
FR_LOOP=$(loop_status franklin-loop)
FR_OUT=$HOME/.blockrun/state/telemetry.json
mkdir -p "$(dirname "$FR_OUT")"
python3 -c "
import json
doc = {
    'instance': 'Franklin',
    'type': 'SELF-funded',
    'wallet': {'address': '$FRANKLIN_ADDR', 'chain': 'solana', 'asset': 'SOL+USDC'},
    'balance_usd': None,
    'balance_native': {'sol': float('$FR_SOL' or 0), 'usdc': float('$FR_USDC' or 0)},
    'pnl': None,
    'loop': {'name': 'franklin-loop', 'launchd_label': 'ai.anicca.franklin-loop', 'status': '$FR_LOOP'},
    'generated_at': '$(now_iso)',
    'generated_at_epoch': $(now_epoch),
    'source': 'public RPC read (api.mainnet-beta.solana.com), no private key accessed'
}
open('$FR_OUT', 'w').write(json.dumps(doc, indent=2) + '\n')
"
echo "wrote $FR_OUT"

# ---- 3. claude-p (PM earner, human-funded) -----------------------------------------------------
CP_BAL=$(erc20 "$POLY" "$PUSD" "$CLAUDEP_ADDR")
CP_LOOP=$(loop_status pm-earner)
CP_PM_JSON=$(pm_positions_json "$CLAUDEP_ADDR")
[ -z "$CP_PM_JSON" ] && CP_PM_JSON='{"open_positions": 0, "value_usd": 0, "unrealized_pnl_usd": 0}'
CP_OUT=$HOME/.anicca-founder/state/telemetry.json
mkdir -p "$(dirname "$CP_OUT")"
python3 -c "
import json
pm = json.loads('''$CP_PM_JSON''')
doc = {
    'instance': 'claude-p',
    'type': 'human-funded',
    'wallet': {'address': '$CLAUDEP_ADDR', 'chain': 'polygon', 'asset': 'pUSD'},
    'balance_usd': float('$CP_BAL' or 0),
    'pnl': {
        'open_positions': pm['open_positions'],
        'position_value_usd': pm['value_usd'],
        'unrealized_pnl_usd': pm['unrealized_pnl_usd'],
    },
    'loop': {'name': 'pm-earner', 'launchd_label': 'ai.anicca.pm-earner', 'status': '$CP_LOOP'},
    'generated_at': '$(now_iso)',
    'generated_at_epoch': $(now_epoch),
    'source': 'public RPC read (polygon-bor-rpc.publicnode.com) + Polymarket data-api, no private key accessed'
}
open('$CP_OUT', 'w').write(json.dumps(doc, indent=2) + '\n')
"
echo "wrote $CP_OUT"

echo "--- done: 3 telemetry.json snapshots written (signature = later step, see #25 TELEM) ---"
