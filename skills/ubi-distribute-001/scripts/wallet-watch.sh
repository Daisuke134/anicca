#!/usr/bin/env bash
# wallet-watch.sh — promotes Anicca's UBI payouts from DRY to LIVE once the
# wallet crosses the revenue threshold.
#
# Triggered hourly by the `anicca-ubi-trigger-check` cron (see watcher-cron.json).
#
# Threshold (gated):
#   - Base mainnet USDC balance >= 1.0
#   - Base mainnet native ETH gas balance >= 0.0005
#
# Side-effect: writes ~/.openclaw/state/ubi-live-flag (JSON) ONCE when the
# threshold first trips. Subsequent runs are no-ops (idempotent — never
# clobbers an existing flag, even if the wallet drains, so a one-time
# manual rollback is a deliberate decision).
#
# payout.sh reads this flag and treats it as UBI_LIVE=1.
#
# Output: a single JSON line on stdout (cron pipes it to #C091G3PKHL2).
set -euo pipefail

ANICCA_WALLET="${ANICCA_WALLET_ADDR:-0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21}"
USDC_THRESHOLD="${UBI_LIVE_USDC_THRESHOLD:-1.0}"
ETH_THRESHOLD="${UBI_LIVE_ETH_THRESHOLD:-0.0005}"
FLAG_PATH="${UBI_LIVE_FLAG:-$HOME/.openclaw/state/ubi-live-flag}"
VIEM_ROOT="${VIEM_NODE_MODULES:-$HOME/.openclaw/npm}"

mkdir -p "$(dirname "$FLAG_PATH")"

# Query Base mainnet via viem. Output JSON: {"base_eth": x, "base_usdc": y}
balances=$(cd "$VIEM_ROOT" && /opt/homebrew/bin/node -e "
const v = require('viem');
const { base } = require('viem/chains');
const ANICCA = process.env.A;
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const erc20 = [{name:'balanceOf',type:'function',inputs:[{type:'address'}],outputs:[{type:'uint256'}],stateMutability:'view'}];
const c = v.createPublicClient({ chain: base, transport: v.http('https://mainnet.base.org') });
Promise.all([
  c.getBalance({ address: ANICCA }),
  c.readContract({ address: USDC, abi: erc20, functionName: 'balanceOf', args: [ANICCA] }),
]).then(([eth, usdc]) => {
  console.log(JSON.stringify({
    base_eth: Number(v.formatUnits(eth, 18)),
    base_usdc: Number(v.formatUnits(usdc, 6)),
  }));
}).catch(e => {
  console.log(JSON.stringify({ error: String(e && e.message || e), base_eth: null, base_usdc: null }));
  process.exit(1);
});
" 2>/dev/null) || true

if [[ -z "$balances" ]]; then
  echo '{"action":"rpc-failed","wallet":"'"$ANICCA_WALLET"'"}'
  exit 1
fi

eth=$(echo "$balances" | jq -r '.base_eth // 0')
usdc=$(echo "$balances" | jq -r '.base_usdc // 0')
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

meets_threshold="false"
if awk -v u="$usdc" -v t="$USDC_THRESHOLD" 'BEGIN{exit !(u + 0 >= t + 0)}' \
   && awk -v e="$eth" -v t="$ETH_THRESHOLD" 'BEGIN{exit !(e + 0 >= t + 0)}'; then
  meets_threshold="true"
fi

if [[ -f "$FLAG_PATH" ]]; then
  # Already promoted — stay promoted, refresh evidence stamp.
  current=$(jq -c '.' "$FLAG_PATH" 2>/dev/null || echo '{}')
  updated=$(echo "$current" | jq -c \
    --arg now "$now" --arg eth "$eth" --arg usdc "$usdc" \
    '. + {last_check_at: $now, last_eth: ($eth|tonumber), last_usdc: ($usdc|tonumber)}')
  echo "$updated" > "$FLAG_PATH"
  echo "{\"action\":\"already-live\",\"flag\":\"$FLAG_PATH\",\"base_eth\":$eth,\"base_usdc\":$usdc}"
  exit 0
fi

if [[ "$meets_threshold" != "true" ]]; then
  echo "{\"action\":\"below-threshold\",\"base_eth\":$eth,\"base_usdc\":$usdc,\"usdc_threshold\":$USDC_THRESHOLD,\"eth_threshold\":$ETH_THRESHOLD,\"checked_at\":\"$now\"}"
  exit 0
fi

# Threshold first crossed — write flag.
jq -nc \
  --arg now "$now" \
  --arg wallet "$ANICCA_WALLET" \
  --arg eth "$eth" \
  --arg usdc "$usdc" \
  --arg ut "$USDC_THRESHOLD" \
  --arg et "$ETH_THRESHOLD" \
  '{promoted_at: $now, wallet: $wallet,
    promoted_eth: ($eth|tonumber), promoted_usdc: ($usdc|tonumber),
    usdc_threshold: ($ut|tonumber), eth_threshold: ($et|tonumber),
    last_check_at: $now,
    last_eth: ($eth|tonumber), last_usdc: ($usdc|tonumber),
    note: "UBI auto-promoted to LIVE — next monthly cron will broadcast on-chain."}' \
  > "$FLAG_PATH"

echo "{\"action\":\"promoted-to-live\",\"flag\":\"$FLAG_PATH\",\"base_eth\":$eth,\"base_usdc\":$usdc}"
