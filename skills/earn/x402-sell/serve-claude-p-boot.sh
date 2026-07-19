#!/usr/bin/env bash
# serve-claude-p-boot.sh — KeepAlive launchd boot of the claude-p x402 seller on :8412.
# Replication test of the x402-sell recipe (SKILL.md) for a SECOND instance on this machine:
# same serve.mjs/primitives.mjs, different payTo (claude-p's own wallet, receiving-only, no key
# needed here) and a second Tailscale Funnel https port (8443 -> 8412) so the CDP Bazaar crawler
# gets an explicit https resource distinct from the founder seller on :8411/443.
set -u
DIR=/Users/operator/anicca/skills/earn/x402-sell
# load CDP facilitator creds (existing account, same as serve-mainnet-boot.sh) — never echoed
set -a; . /Users/operator/.openclaw/.env 2>/dev/null || true; set +a
# NON-DISCRIMINATION (2026-07-19): claude-p runs the SAME concentrated v2 store as franklin —
# same tool, same rail, measure external equally. Force this instance's identity so resale can
# resolve a key (the .env injects a machine-legacy home/key; this store IS claude-p).
export ANICCA_HOME="$HOME/.anicca-founder"
unset BLOCKRUN_WALLET_KEY
export X402_PAYTO="0x810F6D61F7606dEEE2657d3083E150a222Bc29C5"
export X402_PUBLIC_URL="${X402_PUBLIC_URL:-https://aniccanomac-mini-1.tail7a0ba4.ts.net:8443}"
export X402_NETWORK="base"
export X402_PRICE="\$0.003"
export X402_PORT="8412"
PIDS="$(lsof -ti tcp:8412 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# ensure the second Tailscale Funnel https port points at :8412 (idempotent; persists across reboots)
/opt/homebrew/bin/tailscale funnel --bg --https=8443 8412 >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/serve-v2.mjs"
