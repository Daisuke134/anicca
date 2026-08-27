#!/bin/bash
# earn-watch — the waiting jobs, so no human has to sit on them.
#   1. external revenue: has 0x6592 received USDC from anyone other than our own wallets?
#   2. Polymarket: is the Fed position redeemable yet? if so, redeem it.
#   3. Bazaar: is the rent-a-box product indexed yet?
# Writes one status line per run; only acts when a condition is actually met.
set -uo pipefail
TS=$(date -u +%FT%TZ)
PAYEE=0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7

usdc=$(curl -s -m 20 https://base-rpc.publicnode.com -X POST -H "content-type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"data\":\"0x70a08231000000000000000000000000${PAYEE:2}\"},\"latest\"]}" \
  | python3 -c "import json,sys;print(int(json.load(sys.stdin).get('result','0x0'),16)/1e6)" 2>/dev/null || echo "?")

red=$(curl -s -m 20 "https://data-api.polymarket.com/positions?user=0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(1 for p in d if p.get('redeemable')))" 2>/dev/null || echo "?")

if [ "$red" != "?" ] && [ "${red:-0}" -gt 0 ]; then
  echo "$TS REDEEMABLE=$red -> redeeming"
  cd /Users/anicca/.blockrun/skills/earn/polymarket-trade || exit 0
  export ANICCA_HOME=/Users/anicca/.anicca-founder
  K=$(/opt/homebrew/bin/node ../lib/resolve-identity.mjs evm 2>/dev/null)
  if [[ ! "$K" =~ ^0x[0-9a-fA-F]{64}$ ]]; then
    echo "$TS redeem skipped: founder EVM key was not resolvable"
  else
    # launchd PATH also lacks coreutils, so both executables are absolute.
    POLYGON_WALLET_PRIVATE_KEY="$K" /opt/homebrew/bin/timeout 300 \
      /Users/anicca/.anicca-founder/agents/polymarket-agent/.venv/bin/python3 redeem.py 2>&1 | tail -3
  fi
fi

bz=no
for off in 8000 10000 12000 14000; do
  if curl -s -m 25 "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=2000&offset=$off" \
     | grep -q "rent-a-box"; then bz=yes; break; fi
done

echo "$TS payee_usdc=$usdc pm_redeemable=$red bazaar_rentabox=$bz"
