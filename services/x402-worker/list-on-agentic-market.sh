#!/usr/bin/env bash
# Register/validate the deployed x402-cloud route on agentic.market (the x402 Bazaar).
#
# IMPORTANT: agentic.market has NO "POST /api/listings". The Bazaar is a DISCOVERY layer:
# a resource becomes listed automatically once it serves the correct x402 v2 PaymentRequirements
# body (accepts[] with scheme/network/payTo + extensions.bazaar.info) and the facilitator
# crawls/settles it. Our Worker already serves that body (see index.ts send402).
#
# This script:
#   1. Reads the deployed URL from ~/.hermes/state/x402-cloud-deploy.json.
#   2. Validates the endpoint via the agentic.market validator API (so it gets indexed).
#   3. Confirms discoverability via the public services search API.
#   4. Writes the result to ~/.hermes/state/x402-cloud-listing.json.
#
# No API key is required for Bazaar discovery (the marketplace's tagline is "Zero API keys").
set -euo pipefail

STATE_DIR="$HOME/.hermes/state"
DEPLOY_JSON="$STATE_DIR/x402-cloud-deploy.json"
[ -f "$DEPLOY_JSON" ] || { echo "ERROR: $DEPLOY_JSON missing — run deploy.sh first." >&2; exit 1; }

PAID_ROUTE="$(python3 -c "import json;print(json.load(open('$DEPLOY_JSON'))['paid_route'])")"
DOMAIN="$(python3 -c "import json,urllib.parse;print(urllib.parse.urlparse(json.load(open('$DEPLOY_JSON'))['url']).netloc)")"

VALIDATE_API="${AGENTIC_MARKET_VALIDATE_API:-https://api.agentic.market/v1/validate}"
SEARCH_API="${AGENTIC_MARKET_SEARCH_API:-https://api.agentic.market/v1/services/search}"

echo "Validating $PAID_ROUTE on agentic.market Bazaar..."
VAL="$(curl -s -w "\n%{http_code}" -X POST "$VALIDATE_API" \
  -H "content-type: application/json" \
  -d "$(python3 -c "import json,sys;print(json.dumps({'url':sys.argv[1],'method':'GET'}))" "$PAID_ROUTE")" || true)"
VAL_CODE="$(printf '%s' "$VAL" | tail -n1)"
VAL_BODY="$(printf '%s' "$VAL" | sed '$d')"
echo "validate status=$VAL_CODE"
echo "$VAL_BODY"

echo "Checking discovery via services search (domain=$DOMAIN)..."
SEARCH="$(curl -s "$SEARCH_API?q=$DOMAIN" || true)"
echo "$SEARCH" | head -c 800; echo

python3 - "$PAID_ROUTE" "$DOMAIN" "$VAL_CODE" "$VAL_BODY" "$SEARCH" > "$STATE_DIR/x402-cloud-listing.json" <<'PY'
import json, sys, time
paid, domain, vcode, vbody, search = sys.argv[1:6]
try: vbody_j = json.loads(vbody)
except Exception: vbody_j = vbody
try: search_j = json.loads(search)
except Exception: search_j = search
indexed = isinstance(search_j, dict) and any(domain in json.dumps(s) for s in search_j.get("services", []))
print(json.dumps({
  "paid_route": paid,
  "domain": domain,
  "bazaar_validate_status": vcode,
  "bazaar_validate_response": vbody_j,
  "indexed_in_search": indexed,
  "listing_url": f"https://agentic.market/services/{domain.replace('.', '-')}",
  "checked_at": int(time.time()),
}, indent=2))
PY

echo "Listing metadata: $STATE_DIR/x402-cloud-listing.json"
