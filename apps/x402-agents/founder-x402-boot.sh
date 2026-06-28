#!/usr/bin/env bash
# Boot the founder x402 self-facilitating server with the REAL founder key (0x810f).
# Key is read from ~/.anicca-founder/wallet.json at runtime (never on the CLI / ps).
set -eu
cd /Users/anicca/anicca-project/apps/x402-agents
export EVM_PRIVATE_KEY="$(node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));let k=j.private_key;process.stdout.write(k.startsWith("0x")?k:"0x"+k)')"
export X402_WALLET_ADDRESS="0x810f6d61f7606deee2657d3083e150a222bc29c5"
export X402_RPC_URL="https://mainnet.base.org"
export PORT="${PORT:-8410}"
exec node src/server.js
