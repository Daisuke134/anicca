#!/usr/bin/env bash
# whop-driver/api.sh — generic Whop GraphQL invoker (cookie-only, no browser)
#
# Usage:
#   bash api.sh <opName> '<json query body>'
#
# Example:
#   bash api.sh fetchInterestedExperienceIds \
#     '{"query":"query fetchInterestedExperienceIds { viewer { user { interestedExperienceIds } } }","variables":{},"operationName":"fetchInterestedExperienceIds"}'
#
# Prereqs:
#   - CloakBrowser daily-driver running at :9222 with a logged-in Whop tab
#   - patchright venv at ~/.claude/skills/whop-driver/.venv
#
# The cookies are dumped fresh on every call (so re-login is auto-respected).
# After the iframe-sniff harvest catalogs all op signatures (= scripts/sniff_normalize.py),
# higher-level scripts like list_campaigns.sh / join_campaign.sh / submit_clip.sh
# will call THIS wrapper.
set -euo pipefail

OP="${1:?usage: api.sh <opName> <json body>}"
BODY="${2:?usage: api.sh <opName> <json body>}"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" || echo "${BASH_SOURCE[0]}")")" && pwd)"
VENV="$(dirname "$SCRIPT_DIR")/.venv"
COOKIE_FILE=$(mktemp /tmp/whop-cookies.XXXXXX.json)
trap 'rm -f "$COOKIE_FILE"' EXIT

"$VENV/bin/python" - <<'PY' > "$COOKIE_FILE"
import json
from patchright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0]
    print(json.dumps([c for c in ctx.cookies() if "whop.com" in c.get("domain","")]))
PY

COOKIE=$(jq -r 'map("\(.name)=\(.value)") | join("; ")' "$COOKIE_FILE")
CSRF=$(jq -r '.[] | select(.name=="__Host-whop-core.csrf-token") | .value' "$COOKIE_FILE")

curl -sS -X POST "https://whop.com/api/graphql/$OP/" \
  -H "Content-Type: application/json" \
  -H "Cookie: $COOKIE" \
  -H "x-csrf-token: $CSRF" \
  -H "Origin: https://whop.com" \
  -H "Referer: https://whop.com/joined/contentrewards/" \
  -d "$BODY"
