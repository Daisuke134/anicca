#!/usr/bin/env bash
# serve-mainnet-boot.sh — KeepAlive launchd boot of the founder x402 RESEARCH seller on :8411.
# Uses the CDP facilitator (CDP_API_KEY_ID/SECRET from ~/.openclaw/.env) → settles on Base mainnet AND
# lists the endpoint in the x402 Bazaar discovery layer (so buyer agents FIND it). payTo = founder 0x810f
# (USDC lands in our wallet; CDP only facilitates + catalogs, never custodies — no private key on the server).
# Product = $0 research-product.mjs (Wikipedia + HN + Jina). Public via Tailscale Funnel.
set -u
DIR=/Users/anicca/anicca/skills/earn/x402-sell
# load CDP facilitator creds (existing account) — never echoed
set -a; . /Users/anicca/.openclaw/.env 2>/dev/null || true; set +a
export X402_PAYTO="0x810f6d61f7606deee2657d3083e150a222bc29c5"
# public HTTPS origin the CDP Bazaar crawler probes — must be the real reachable https:// (funnel origin),
# else x402-express derives an http:// resource URL the crawler can't reach and never indexes us.
export X402_PUBLIC_URL="${X402_PUBLIC_URL:-https://aniccanomac-mini-1.tail7a0ba4.ts.net}"
export X402_NETWORK="base"
export X402_PRICE="\$0.003"
export X402_PORT="8411"
PIDS="$(lsof -ti tcp:8411 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# ensure the Tailscale Funnel points at :8411 (idempotent; persists across reboots)
/opt/homebrew/bin/tailscale funnel --bg 8411 >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/serve.mjs"
