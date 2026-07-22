#!/usr/bin/env bash
# KeepAlive entrypoint for franklin1's demand-proven x402 image resale product.
set -u
DIR=/Users/anicca/anicca/skills/earn/x402-sell
set -a; . /Users/anicca/.openclaw/.env 2>/dev/null || true; set +a
# The shared env carries a legacy wallet. This service must spend upstream and receive revenue only
# through franklin1's own wallet/home.
export ANICCA_HOME="$HOME/.blockrun"
unset BLOCKRUN_WALLET_KEY
export X402_PAYTO="0x3EcCAD24794ca298D25378E9902A251322ea8749"
export X402_IMAGE_PORT="8093"
export X402_IMAGE_PUBLIC_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net"
PIDS="$(lsof -ti tcp:8093 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# Add only /image. Existing / and /mcp mounts on :443 remain intact.
/opt/homebrew/bin/tailscale funnel --bg --https=443 --set-path=/image http://127.0.0.1:8093/image >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/image-server.mjs"
