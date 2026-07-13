#!/usr/bin/env bash
# Launch the x402 earning gig: slop-scan API behind an ag402 USDC paywall.
# ★ no-human, no-captcha, no-signup, no-Dais-money — pays USDC to MY Solana wallet ★
# Any AI/model can run this; swap PUBKEY to its own wallet.
set -euo pipefail

VENV="$HOME/.cache/ag402-venv/bin"
GIG_DIR="$HOME/.claude/skills/earn-gig/scripts/x402_gig"
PUBKEY="${GIG_PUBKEY:-xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H}"   # my Solana wallet
PRICE="${GIG_PRICE:-0.002}"
API_PORT="${GIG_API_PORT:-8799}"
GW_PORT="${GIG_GW_PORT:-8402}"
MODE="${X402_MODE:-test}"   # set X402_MODE=production for real mainnet USDC

cd "$GIG_DIR"
# clean stale
lsof -ti :"$API_PORT" :"$GW_PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# 1. backend (deterministic, $0 to serve)
nohup "$VENV/uvicorn" slop_scan_api:app --host 127.0.0.1 --port "$API_PORT" >/tmp/slop_api.log 2>&1 &
sleep 3

# 2. ag402 paywall gateway (seller-no-key: only needs public address)
X402_MODE="$MODE" nohup "$VENV/ag402" serve \
  --target "http://127.0.0.1:$API_PORT" --host 0.0.0.0 --port "$GW_PORT" \
  --price "$PRICE" --address "$PUBKEY" >/tmp/ag402_gw.log 2>&1 &
sleep 5

echo "gig live: paywall http://0.0.0.0:$GW_PORT/scan  ($PRICE USDC/call → $PUBKEY, mode=$MODE)"
grep -iE "started|error|already" /tmp/ag402_gw.log | head -3
# self-verify 402
curl -sS --max-time 8 -o /dev/null -w "402 check: %{http_code}\n" -X POST "http://127.0.0.1:$GW_PORT/scan" \
  -H 'Content-Type: application/json' -d '{"text":"delve"}'
