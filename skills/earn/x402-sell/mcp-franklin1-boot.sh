#!/usr/bin/env bash
# KeepAlive entrypoint for franklin1's MonetizedMCP adapter.
set -u
DIR=/Users/anicca/anicca/skills/earn/x402-sell
set -a; . /Users/anicca/.openclaw/.env 2>/dev/null || true; set +a
export ANICCA_HOME="$HOME/.blockrun"
unset BLOCKRUN_WALLET_KEY
export X402_PAYTO="0x3EcCAD24794ca298D25378E9902A251322ea8749"
export X402_PORT="8414"
export PORT="8090"
PIDS="$(lsof -ti tcp:8090 2>/dev/null || true)"; [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
sleep 1
# Public routing is owned by the additive `franklin1-mcp` tsbridge node. Tailscale Funnel cannot
# listen on :10001; only 443/8443/10000 are externally reachable.
exec /usr/bin/env node "$DIR/mcp-server.mjs"
