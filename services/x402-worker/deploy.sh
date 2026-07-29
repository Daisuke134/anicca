#!/usr/bin/env bash
# Deploy the x402-cloud Worker to Cloudflare.
#
# Reads CLOUDFLARE_API_TOKEN (+ optional CLOUDFLARE_ACCOUNT_ID) from ~/.hermes/.env,
# falling back to $HOME/.local/state/life-manager/.env. Creates the NONCE_KV namespace if needed, patches its
# id into wrangler.toml, runs `wrangler deploy`, and writes the deployed URL to
# ~/.hermes/state/x402-cloud-deploy.json.
#
# Never echoes the token value.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

load_env() { # file key
  [ -f "$1" ] || return 1
  local v
  v="$(grep -E "^$2=" "$1" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
  [ -n "$v" ] && printf '%s' "$v"
}

CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-$(load_env "$HOME/.hermes/.env" CLOUDFLARE_API_TOKEN || load_env "$HOME/.local/state/life-manager/.env" CLOUDFLARE_API_TOKEN || true)}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-$(load_env "$HOME/.hermes/.env" CLOUDFLARE_ACCOUNT_ID || load_env "$HOME/.local/state/life-manager/.env" CLOUDFLARE_ACCOUNT_ID || true)}"

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN missing in ~/.hermes/.env and $HOME/.local/state/life-manager/.env." >&2
  echo "Provision via camofox autonomous signup at cloudflare.com (HARD RULE #-1), then re-run." >&2
  exit 2
fi
export CLOUDFLARE_API_TOKEN
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] && export CLOUDFLARE_ACCOUNT_ID

echo "Cloudflare token loaded (len=${#CLOUDFLARE_API_TOKEN})."

# 1. Ensure NONCE_KV namespace exists, capture its id.
echo "Ensuring NONCE_KV namespace..."
KV_JSON="$(npx wrangler kv namespace create NONCE_KV 2>&1 || true)"
KV_ID="$(printf '%s' "$KV_JSON" | grep -oE '"?id"?[ =:]+"?[0-9a-f]{32}"?' | grep -oE '[0-9a-f]{32}' | head -1 || true)"
if [ -z "$KV_ID" ]; then
  # Already exists — list and grab it.
  KV_ID="$(npx wrangler kv namespace list 2>/dev/null | python3 -c "import json,sys
try:
  data=json.load(sys.stdin)
except Exception:
  data=[]
for ns in data:
  if ns.get('title','').endswith('NONCE_KV') or ns.get('title','')=='anicca-x402-NONCE_KV':
    print(ns['id']); break" || true)"
fi
if [ -z "$KV_ID" ]; then
  echo "ERROR: could not determine NONCE_KV id." >&2
  echo "$KV_JSON" >&2
  exit 3
fi
echo "NONCE_KV id resolved (32 hex)."

# 2. Patch wrangler.toml with the real KV id.
python3 - "$KV_ID" <<'PY'
import pathlib, re, sys
kv_id = sys.argv[1]
p = pathlib.Path("wrangler.toml")
t = p.read_text()
t = re.sub(r'id = "[^"]*"', f'id = "{kv_id}"', t)
p.write_text(t)
print("wrangler.toml KV id patched.")
PY

# 3. Deploy.
echo "Deploying Worker..."
DEPLOY_OUT="$(npx wrangler deploy 2>&1)"
echo "$DEPLOY_OUT"
URL="$(printf '%s' "$DEPLOY_OUT" | grep -oE 'https://[a-zA-Z0-9.-]+\.workers\.dev' | head -1 || true)"
if [ -z "$URL" ]; then
  echo "ERROR: deploy did not return a workers.dev URL." >&2
  exit 4
fi

# 4. Persist deploy metadata.
STATE_DIR="$HOME/.hermes/state"
mkdir -p "$STATE_DIR"
python3 - "$URL" "$KV_ID" > "$STATE_DIR/x402-cloud-deploy.json" <<'PY'
import json, sys, time
print(json.dumps({
  "worker": "anicca-x402",
  "url": sys.argv[1],
  "paid_route": sys.argv[1] + "/paid",
  "health_route": sys.argv[1] + "/health",
  "kv_namespace": "NONCE_KV",
  "kv_id": sys.argv[2],
  "pay_to": "0xB9dd3B67921B354c656523d6851537988F31DD56",
  "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "network": "base",
  "chain_id": 8453,
  "price_atomic": 1000,
  "deployed_at": int(time.time()),
}, indent=2))
PY

echo "Deployed: $URL"
echo "Metadata: $STATE_DIR/x402-cloud-deploy.json"
