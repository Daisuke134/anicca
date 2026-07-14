#!/usr/bin/env bash
# seller-boot.sh — per-instance x402 seller entrypoint for a KeepAlive supervisor (launchd plist
# written by ../run.sh strategy=x402). Sources facilitator creds then exec's the seller.
# Env from the plist: X402_PAYTO, X402_PORT, X402_PUBLIC_URL, OPENCLAW_ENV_FILE(optional).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
set -a; . "${OPENCLAW_ENV_FILE:-$HOME/.openclaw/.env}" 2>/dev/null || true; set +a
exec /usr/bin/env node "$DIR/serve.mjs"
