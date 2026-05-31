#!/usr/bin/env bash
# anicca-wallet/scripts/balance.sh
# Anicca wallet の Base chain USDC + ETH balance を query

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

ADDR="${ANICCA_WALLET_ADDR:-$(jq -r .address "$HOME/.openclaw/skills/anicca-wallet/state/wallet.json" 2>/dev/null)}"
if [ -z "$ADDR" ] || [ "$ADDR" = "null" ]; then
  echo "[anicca-wallet/balance] ERR: no wallet found. Run generate.sh first." >&2
  exit 1
fi

# Base RPC (free public endpoint)
RPC="${BASE_RPC:-https://mainnet.base.org}"

# USDC on Base = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
USDC_CONTRACT="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Query ETH balance
ETH_HEX=$(curl -sS -X POST "$RPC" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$ADDR\",\"latest\"],\"id\":1}" | jq -r .result)

# Query USDC balanceOf(address) = function selector 0x70a08231 + 32-byte padded address
ADDR_PADDED=$(echo "${ADDR#0x}" | python3 -c "import sys; print(sys.stdin.read().strip().lower().zfill(64))")
CALL_DATA="0x70a08231${ADDR_PADDED}"
USDC_HEX=$(curl -sS -X POST "$RPC" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC_CONTRACT\",\"data\":\"$CALL_DATA\"},\"latest\"],\"id\":1}" | jq -r .result)

# Convert hex → decimal → human
ETH_WEI=$(python3 -c "print(int('$ETH_HEX', 16) if '$ETH_HEX' not in ['null', '0x'] else 0)")
USDC_RAW=$(python3 -c "print(int('$USDC_HEX', 16) if '$USDC_HEX' not in ['null', '0x'] else 0)")
ETH_HUMAN=$(python3 -c "print(f'{$ETH_WEI / 10**18:.6f}')")
USDC_HUMAN=$(python3 -c "print(f'{$USDC_RAW / 10**6:.2f}')")

jq -n \
  --arg addr "$ADDR" \
  --arg network "base" \
  --arg eth_balance "$ETH_HUMAN" \
  --arg usdc_balance "$USDC_HUMAN" \
  --arg eth_wei "$ETH_WEI" \
  --arg usdc_raw "$USDC_RAW" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    address: $addr,
    network: $network,
    eth_balance: ($eth_balance | tonumber),
    usdc_balance: ($usdc_balance | tonumber),
    eth_wei: $eth_wei,
    usdc_raw: $usdc_raw,
    chain_explorer: "https://basescan.org/address/\($addr)",
    queried_at: $ts
  }' | tee "$HOME/.openclaw/skills/anicca-wallet/state/last-balance.json"
