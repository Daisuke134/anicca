#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# founder-serve.sh — KeepAlive launchd boot of the FOUNDER x402 seller, port 8410.
# ★ Runs the SELF-FACILITATING Base-MAINNET server (apps/x402-agents/src/server.js), NOT the old testnet
#   serve.mjs. In-process facilitator signed by the founder key (0x810f, ~/.anicca-founder/wallet.json),
#   settles real USDC on Base mainnet — verified on-chain 2026-06-28 (tx 0x71d4ca08). exec so launchd
#   KeepAlive supervises node directly. ★
set -u
SERVE="$LIFE_MANAGER_REPO/apps/x402-agents/src/server.js"
# founder key read at runtime from the founder body (never on the CLI / ps).
export EVM_PRIVATE_KEY="$(node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));let k=j.private_key;process.stdout.write(k.startsWith("0x")?k:"0x"+k)')"
export X402_WALLET_ADDRESS="0x810f6d61f7606deee2657d3083e150a222bc29c5"   # ★ founder wallet — NOT the automaton 0xa3CDd4 ★
export X402_RPC_URL="https://mainnet.base.org"
export PORT="8410"
# kill any stale founder serve on this port (match the port, not a broad pkill that would hit other sellers)
PIDS="$(lsof -ti tcp:8410 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
exec /usr/bin/env node "$SERVE"
