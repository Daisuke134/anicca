#!/usr/bin/env bash
# IG Personal signup via Playwright. Phone-number flow (NOT {{profile.lateness.stakeholders.channel}}).
# STUB: real Playwright code in scripts/signup-personal.spec.ts (TODO).
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

PHONE=$(python3 -c "import json; print(json.load(open('$ACCOUNTS_DIR/tiktok.json')).get('phone',''))" 2>/dev/null)
[ -n "$PHONE" ] || { echo "❌ no phone — run tiktok-account-factory first"; exit 51; }

echo "🛠 STUB: signup-personal.sh — Playwright spec not yet implemented."
echo "  Phone: $PHONE (shared with TikTok account, intentional per Shalev L1)"
echo "  Persona: $PERSONA"
echo ""
echo "  Implementation reference:"
echo "    1. Playwright open https://www.instagram.com/accounts/{{profile.lateness.stakeholders.channel}}signup/"
echo "    2. Click 'phone' tab → enter \$PHONE → solve captcha"
echo "    3. Wait for SMS code (otp-relay.sh polls SMSPool, falls back to Slack)"
echo "    4. Enter username (slug-based: @<persona-slug>)"
echo "    5. Save credentials to \$ACCOUNTS_DIR/instagram.json with status='ghost_mode'"
echo "    6. Set NO PFP / NO bio / NO link — same Shalev L2 ghost mode pattern"
echo ""
echo "  See ~/.openclaw/skills/instagram-account-factory/scripts/signup-personal.spec.ts (to be written)"
exit 99
