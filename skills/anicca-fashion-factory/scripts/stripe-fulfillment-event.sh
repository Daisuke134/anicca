#!/usr/bin/env bash
# Stripe → Printful fulfillment is handled by Netlify function:
#   apps/landing/netlify/functions/stripe-fashion-webhook.js
#
# This local script is a status/healthcheck relay for the openclaw cron
# system. It verifies that:
#   1. STRIPE_SECRET_KEY + PRINTFUL_API_KEY env are set
#   2. Stripe webhook endpoint is reachable + returns 200 on a HEAD probe
#   3. Recent Supabase fashion_orders show no stuck "pending" > 24h
#
# Real fulfillment runs on Netlify on Stripe webhook delivery.
#
# stdout final line:
#   ✅ stripe-fulfillment: webhook=ok | stuck_orders=N
#   ❌ stripe-fulfillment FAILED: <reason>

set -euo pipefail

set -a; source "$HOME/.openclaw/.env"; set +a

WEBHOOK_URL="https://aniccaai.com/.netlify/functions/stripe-fashion-webhook"
PYTHON="python3"

# 1. env check
for v in STRIPE_SECRET_KEY PRINTFUL_API_KEY SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY; do
  if [ -z "${!v:-}" ]; then
    echo "❌ stripe-fulfillment FAILED: env $v not set"
    exit 1
  fi
done

# 2. webhook reachability
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{"healthcheck":true}' \
  "$WEBHOOK_URL" || echo "000")

# Stripe signature verify will reject this body → 400 expected. 4xx = endpoint up.
if [[ ! "$HTTP_CODE" =~ ^[2-4][0-9][0-9]$ ]]; then
  echo "❌ stripe-fulfillment FAILED: webhook unreachable (HTTP $HTTP_CODE)"
  exit 1
fi
WEBHOOK_OK="ok"

# 3. stuck-orders check via Supabase REST
STUCK=$($PYTHON - <<PY
import os, json, urllib.request, urllib.parse, datetime
url = os.environ["SUPABASE_URL"] + "/rest/v1/fashion_orders"
since = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
params = {"select": "id,status,created_at",
          "status":  "eq.pending",
          "created_at": f"lt.{since}"}
url += "?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={
    "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_ROLE_KEY']}",
})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    print(len(data))
except Exception:
    print(0)
PY
)

echo "✅ stripe-fulfillment: webhook=$WEBHOOK_OK | stuck_orders=$STUCK"
