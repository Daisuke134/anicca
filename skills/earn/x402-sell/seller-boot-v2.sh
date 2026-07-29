#!/usr/bin/env bash
# seller-boot-v2.sh — per-instance x402 seller entrypoint for a loop-owned KeepAlive supervisor
# (launchd plist written by ../run.sh strategy=x402 action=ensure), v2 protocol variant.
# Same dependency-resolution recipe as seller-boot.sh (runtime/self-update-skills.sh rsyncs
# repo/skills -> ANICCA_HOME/skills with --exclude='node_modules', so ANICCA_HOME's copy has the
# source but not the dependency tree — exec the copy that HAS @coinbase/x402 installed), but execs
# serve-v2.mjs (@x402/express@2.17.0) instead of the v1 serve.mjs: SELF-STORE-1 (2026-07-18) points
# every loop-owned seller at the same v2 protocol the hand-made per-instance boot scripts already
# use (serve-franklin1-boot.sh / serve-franklin2-boot.sh / serve-claude-p-boot.sh).
# Env from the plist: X402_PAYTO, X402_PORT, X402_PUBLIC_URL, OPENCLAW_ENV_FILE(optional).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$DIR/node_modules/@coinbase/x402" ]; then
  REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)}}"
  [ -d "$REPO/skills/earn/x402-sell/node_modules/@coinbase/x402" ] && DIR="$REPO/skills/earn/x402-sell"
fi
set -a; . "${OPENCLAW_ENV_FILE:-$HOME/.local/state/life-manager/.env}" 2>/dev/null || true; set +a
exec /usr/bin/env node "$DIR/serve-v2.mjs"
