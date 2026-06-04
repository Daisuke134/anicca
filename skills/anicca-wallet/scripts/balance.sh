#!/usr/bin/env bash
# anicca-wallet/scripts/balance.sh
# Read-only Base-chain USDC + ETH balance probe. Emits ONE JSON object on stdout.
# No state writes (balance_watch.sh handles persistence).
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

ADDR=$(python3 -c "
import sys
sys.path.insert(0, '$SKILL_DIR/scripts')
import wallet_lib
print(wallet_lib.address_only())
")

RPC="${BASE_RPC:-https://mainnet.base.org}"
USDC_CONTRACT="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # USDC on Base mainnet

# ETH balance
ETH_HEX=$(curl -sS --max-time 8 -X POST "$RPC" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}" \
  | /usr/bin/jq -r .result)

# USDC balanceOf(ADDR) — function selector 0x70a08231 + 32-byte left-padded address
ADDR_PADDED=$(python3 -c "print('${ADDR#0x}'.lower().zfill(64))")
CALL_DATA="0x70a08231${ADDR_PADDED}"
USDC_HEX=$(curl -sS --max-time 8 -X POST "$RPC" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC_CONTRACT\",\"data\":\"$CALL_DATA\"},\"latest\"],\"id\":1}" \
  | /usr/bin/jq -r .result)

ETH_WEI=$(python3 -c "h='$ETH_HEX'; print(int(h,16) if h not in ('null','0x','') else 0)")
USDC_RAW=$(python3 -c "h='$USDC_HEX'; print(int(h,16) if h not in ('null','0x','') else 0)")
ETH_HUMAN=$(python3 -c "print(f'{$ETH_WEI / 10**18:.6f}')")
USDC_HUMAN=$(python3 -c "print(f'{$USDC_RAW / 10**6:.2f}')")

/usr/bin/jq -c -n \
  --arg address "$ADDR" \
  --arg network "base" \
  --arg usdc "$USDC_HUMAN" \
  --arg eth "$ETH_HUMAN" \
  --arg eth_wei "$ETH_WEI" \
  --arg usdc_raw "$USDC_RAW" \
  --arg queried_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    address: $address,
    network: $network,
    usdc: ($usdc | tonumber),
    eth:  ($eth  | tonumber),
    usdc_raw_atomic: ($usdc_raw | tonumber),
    eth_wei: ($eth_wei | tonumber),
    chain_explorer: "https://basescan.org/address/\($address)",
    queried_at: $queried_at
  }'
