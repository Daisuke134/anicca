#!/usr/bin/env bash
# Gmail signup — REAL SIM required. Google bans VOIP / Google Voice / SMSPool numbers.
# Dais creates the Gmail manually; this script just registers it in the registry.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
GMAILS_REGISTRY="$ROOT/accounts/_gmails_registry.json"
mkdir -p "$ROOT/accounts"

[ -f "$GMAILS_REGISTRY" ] || echo '{"gmails":[]}' > "$GMAILS_REGISTRY"

cat <<'EOF'
🛑 GMAIL SIGNUP — Manual step required

Google's bot detection on Gmail signup is the strictest of all 3 platforms.
Even 100% Playwright automation gets caught at OTP. So:

1. (Manual, Dais on iPhone) Open accounts.google.com/signup
2. Use REAL US phone number (Mint Mobile, NOT Google Voice / VOIP / SMSPool)
3. Suggested {{profile.lateness.stakeholders.channel}} pattern: anicca.<NN>@gmail.com (NN = 01, 02, 03, 04, 05)
4. Once created, run:

   python3 -c "
import json, os, sys
path = os.path.expanduser('~/anicca-monk-factory/accounts/_gmails_registry.json')
reg = json.load(open(path))
reg['gmails'].append({
    '{{profile.lateness.stakeholders.channel}}': 'anicca.01@gmail.com',  # ← edit
    'phone': '+1...',                 # ← edit
    'created_at': '2026-...',         # ← edit
    'brand_accounts': []              # filled in by youtube-account-factory
})
json.dump(reg, open(path, 'w'), indent=2)
print('registered')
   "

This Gmail can host up to 6 Brand Accounts (= 6 personas worth of YouTube channels).
EOF
