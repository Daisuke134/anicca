#!/usr/bin/env bash
# KeepAlive entrypoint for franklin2's demand-proven x402 image resale product.
set -u
DIR=/Users/anicca/anicca/skills/earn/x402-sell
set -a; . /Users/anicca/.openclaw/.env 2>/dev/null || true; set +a
# The shared env carries a legacy wallet. This service must spend upstream and receive revenue only
# through franklin2's own wallet/home.
export ANICCA_HOME="$HOME/.franklin2-home/.blockrun"
unset BLOCKRUN_WALLET_KEY
export X402_PAYTO="0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9"
export X402_IMAGE_PORT="8094"
export X402_IMAGE_PUBLIC_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000"
export X402_IMAGE_UPSTREAM_OPENAPI="http://127.0.0.1:8413/openapi.json"
PIDS="$(lsof -ti tcp:8094 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# Add only exact discovery/product paths. Existing / and /mcp mounts on :10000 remain intact.
/opt/homebrew/bin/tailscale funnel --bg --https=10000 --set-path=/image http://127.0.0.1:8094/image >/dev/null 2>&1 || true
/opt/homebrew/bin/tailscale funnel --bg --https=10000 --set-path=/openapi.json http://127.0.0.1:8094/openapi.json >/dev/null 2>&1 || true
exec /usr/bin/env node "$DIR/image-server.mjs"
