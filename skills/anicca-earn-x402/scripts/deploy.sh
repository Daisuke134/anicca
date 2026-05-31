#!/usr/bin/env bash
# anicca-earn-x402/scripts/deploy.sh
# Cloudflare Worker に anicca-earn-x402 を deploy

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-x402"
WORKER_DIR="$SKILL_DIR/workers"

# Prerequisites
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  echo "[deploy] CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID required (= anicca-cloudflare-account skill が先 に走る必要)" >&2
  echo "[deploy] dry-run: would deploy x402 worker to anicca.workers.dev" >&2
  exit 2
fi

WALLET_ADDR="${ANICCA_WALLET_ADDR:-}"
if [ -z "$WALLET_ADDR" ]; then
  echo "[deploy] ANICCA_WALLET_ADDR required (anicca-wallet skill が先)" >&2
  exit 3
fi

cd "$WORKER_DIR"

# Install wrangler if not present
if ! command -v wrangler &>/dev/null && ! command -v npx &>/dev/null; then
  echo "[deploy] need wrangler CLI: npm install -g wrangler" >&2
  exit 4
fi

# Inject account_id into wrangler.toml (in-place if not already set)
if ! grep -q "^account_id = \"$CLOUDFLARE_ACCOUNT_ID\"" wrangler.toml; then
  sed -i.bak "s|^account_id = \".*\"|account_id = \"$CLOUDFLARE_ACCOUNT_ID\"|" wrangler.toml
fi

# Create KV namespace if missing
if ! grep -q "^id = \"[a-f0-9]" wrangler.toml; then
  echo "[deploy] creating KV namespace ANICCA_KV..."
  NS_JSON=$(npx wrangler kv:namespace create "ANICCA_KV" 2>&1 || true)
  NS_ID=$(echo "$NS_JSON" | grep -oE 'id = "[a-f0-9]+"' | head -1 | cut -d'"' -f2)
  if [ -n "$NS_ID" ]; then
    sed -i.bak "s|^id = \"\"|id = \"$NS_ID\"|" wrangler.toml
  fi
fi

# Create R2 bucket if missing (idempotent)
npx wrangler r2 bucket create anicca-pdfs 2>&1 | grep -E "Created|already exists" || true

# Push secrets
echo "$WALLET_ADDR" | npx wrangler secret put ANICCA_WALLET_ADDR
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "$ANTHROPIC_API_KEY" | npx wrangler secret put ANTHROPIC_API_KEY
fi

# Deploy
DEPLOY_OUT=$(npx wrangler deploy 2>&1)
echo "$DEPLOY_OUT"

URL=$(echo "$DEPLOY_OUT" | grep -oE 'https://[a-z0-9-]+\.workers\.dev' | head -1)
if [ -n "$URL" ]; then
  STATE="$SKILL_DIR/state"
  mkdir -p "$STATE"
  jq -n --arg url "$URL" --arg addr "$WALLET_ADDR" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{worker_url: $url, wallet: $addr, deployed_at: $ts, routes: ["/qa","/research","/x-post","/pdf/:slug","/build","/.well-known/x402"]}' \
    > "$STATE/deploy.json"
  echo "[deploy] ✓ $URL"
fi
