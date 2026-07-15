#!/usr/bin/env bash
# serve-franklin1-boot.sh — KeepAlive launchd boot of franklin1's (~/.blockrun) x402 seller on :8414.
# Same recipe as serve-claude-p-boot.sh/serve-mainnet-boot.sh/serve-franklin2-boot.sh (x402-sell/
# SKILL.md), a fourth replication: same serve.mjs/primitives.mjs, franklin1's OWN payTo
# (receiving-only, no key needed here) and its own Tailscale Funnel https port so the CDP Bazaar
# crawler gets an explicit https resource distinct from the other sellers on :8411/:8412/:8413.
#
# WHY this exists (x402-seller-persistence 2026-07-14): franklin1 had NO dedicated x402 seller at
# all (no boot script, no port of its own in its loop plist) — when its earn-loop picked the
# x402_sell slot, run.sh's in-wake nohup fallback used the bare default port 8404, which was
# ALREADY occupied by an unrelated stray process (a different wallet's payTo). run.sh's curl-ping
# guard saw that stray process as "already up" and never booted franklin1's own seller, so a
# franklin1 x402_sell wake silently reported success while never actually exposing franklin1's OWN
# payTo. A dedicated port + dedicated KeepAlive job removes the collision permanently.
set -u
DIR=/Users/anicca/anicca/skills/earn/x402-sell
# load CDP facilitator creds (existing account, same as the other boot scripts) — never echoed
set -a; . /Users/anicca/.openclaw/.env 2>/dev/null || true; set +a
export X402_PAYTO="0x3EcCAD24794ca298D25378E9902A251322ea8749"
export X402_PUBLIC_URL="${X402_PUBLIC_URL:-https://aniccanomac-mini-1.tail7a0ba4.ts.net:10001}"
export X402_NETWORK="base"
export X402_PRICE="\$0.003"
export X402_PORT="8414"
PIDS="$(lsof -ti tcp:8414 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# ensure the Tailscale Funnel https port points at :8414 (idempotent; persists across reboots)
/opt/homebrew/bin/tailscale funnel --bg --https=10001 8414 >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/serve.mjs"
