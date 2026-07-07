#!/usr/bin/env bash
# Keep Anicca's INBOUND x402 paid endpoint live + publicly reachable.
# Runs the standalone Node server (server.mjs) and a free cloudflared quick tunnel.
# No Cloudflare account / Turnstile needed (the prior deploy.sh blocker). When an external
# agent pays /paid (buyer-signed EIP-3009 -> on-chain settle), the earn loop's EARN_SOURCE=x402
# preset verifies that tx and records GATE-0.
#
# Usage: ./serve.sh            # start (idempotent)
#        URL is written to state/public-url.txt
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
PORT="${PORT:-8402}"
mkdir -p state

# 1. server (idempotent)
if ! curl -s -m3 "http://localhost:$PORT/health" >/dev/null 2>&1; then
  STATE_DIR="$HERE/state" PORT="$PORT" nohup node server.mjs > state/server.log 2>&1 &
  for i in $(seq 1 10); do sleep 1; curl -s -m3 "http://localhost:$PORT/health" >/dev/null 2>&1 && break; done
fi
curl -s -m3 "http://localhost:$PORT/health" >/dev/null 2>&1 || { echo "server failed to start" >&2; exit 1; }

# 2. public quick tunnel (idempotent: reuse a live one if present)
URL=""
[ -f state/public-url.txt ] && URL="$(cat state/public-url.txt)"
if [ -z "$URL" ] || ! curl -s -m6 --resolve "$(echo "$URL"|sed 's#https://##'):443:104.16.230.132" "$URL/health" >/dev/null 2>&1; then
  pkill -f "tunnel --no-autoupdate --url http://localhost:$PORT" 2>/dev/null
  nohup cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" > state/tunnel.log 2>&1 &
  for i in $(seq 1 25); do
    sleep 2
    URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' state/tunnel.log | head -1)"
    [ -n "$URL" ] && break
  done
  echo "$URL" > state/public-url.txt
fi

echo "x402-serve live:"
echo "  local : http://localhost:$PORT"
echo "  public: $URL"
echo "  routes: /health /paid(402) /openapi.json /.well-known/x402"
echo "  pay_to: 0xB9dd3B67921B354c656523d6851537988F31DD56 (USDC on Base)"
