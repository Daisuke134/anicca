#!/usr/bin/env bash
# serve-mainnet-boot.sh — KeepAlive launchd boot of the founder x402 RESEARCH seller on :8411.
# Self-facilitating Base-mainnet (founder 0x810f, key read at runtime from ~/.anicca-founder/wallet.json).
# Public via Tailscale Funnel → https://aniccanomac-mini-1.tail7a0ba4.ts.net (stable, real cert, $0).
set -u
DIR=/Users/anicca/anicca-human-funded/skills/earn/x402-sell
export EVM_PRIVATE_KEY="$(node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));let k=j.private_key;process.stdout.write(k.startsWith("0x")?k:"0x"+k)')"
export X402_WALLET_ADDRESS="0x810f6d61f7606deee2657d3083e150a222bc29c5"
export X402_RPC_URL="https://mainnet.base.org"
export X402_PORT="8411"
PIDS="$(lsof -ti tcp:8411 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# ensure the Tailscale Funnel is pointed at :8411 (idempotent; persists across reboots)
/opt/homebrew/bin/tailscale funnel --bg 8411 >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/serve-mainnet.mjs"
