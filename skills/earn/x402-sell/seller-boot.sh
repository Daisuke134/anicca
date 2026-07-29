#!/usr/bin/env bash
# seller-boot.sh — per-instance x402 seller entrypoint for a KeepAlive supervisor (launchd plist
# written by ../run.sh strategy=x402). Sources facilitator creds then exec's the seller.
# Env from the plist: X402_PAYTO, X402_PORT, X402_PUBLIC_URL, OPENCLAW_ENV_FILE(optional).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
# runtime/self-update-skills.sh rsyncs repo/skills → ANICCA_HOME/skills with --exclude='node_modules'
# (right call: 635M per instance would fill the disk). So this dir has serve.mjs but no dependencies,
# and node dies on ERR_MODULE_NOT_FOUND '@coinbase/x402' before binding the port — which is why every
# loop-spawned seller was in a crash loop (measured 2026-07-16: runs=213/168/213, all exit 1). The
# serve.mjs files are byte-identical, so exec the copy that HAS the dependency tree.
if [ ! -d "$DIR/node_modules/@coinbase/x402" ]; then
  REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)}}"
  [ -d "$REPO/skills/earn/x402-sell/node_modules/@coinbase/x402" ] && DIR="$REPO/skills/earn/x402-sell"
fi
set -a; . "${OPENCLAW_ENV_FILE:-$HOME/.local/state/life-manager/.env}" 2>/dev/null || true; set +a
exec /usr/bin/env node "$DIR/serve.mjs"
