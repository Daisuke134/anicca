#!/usr/bin/env bash
# Create a YouTube Brand Account under a parent Gmail. Playwright automation.
# STUB.
set -euo pipefail
PERSONA="${1:?persona required}"
GMAIL="${2:?gmail required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

cat <<EOF
🛠 STUB: brand-account-create.sh — Playwright spec not yet implemented.

Persona: $PERSONA
Parent Gmail: $GMAIL

Implementation reference (when ready):
1. Playwright login as \$GMAIL
2. Open https://www.youtube.com/account_advanced
3. Click "Add or manage your channels" → "Create a channel"
4. Use a Brand Account → channel name = "@$PERSONA"
5. After creation, capture channel_id (UC...)
6. Save to:
   ~/anicca-monk-factory/accounts/$PERSONA/youtube.json
   {"gmail_account": "$GMAIL", "channel_handle": "@$PERSONA",
    "channel_id": "UC...", "type": "brand_account", "status": "ready",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
7. Append channel_id to gmails registry under \$GMAIL.brand_accounts[]:
   ~/anicca-monk-factory/accounts/_gmails_registry.json

DOM selectors are stable enough for Playwright; YT brand account flow is
forgiving (no captcha after Gmail trust is established).
EOF
exit 99
