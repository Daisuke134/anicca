#!/usr/bin/env bash
# Personal → Business switch. Run AFTER 7-day warmup. Requires Dais to create matching FB Page.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

[ -f "$ACCOUNTS_DIR/instagram.json" ] || { echo "❌ no instagram.json — Personal signup not done"; exit 61; }
WARMUP_DAYS=$(python3 -c "
import json, datetime
d = json.load(open('$ACCOUNTS_DIR/instagram.json'))
created = datetime.datetime.fromisoformat(d.get('created_at','2026-01-01T00:00:00Z').replace('Z','+00:00'))
delta = datetime.datetime.now(datetime.timezone.utc) - created
print(delta.days)
" 2>/dev/null || echo 0)

if [ "$WARMUP_DAYS" -lt 7 ]; then
  echo "🛑 Account is only $WARMUP_DAYS days old — wait at least 7 before Business switch (Shalev L2 ghost mode requirement)"
  exit 62
fi

cat <<EOF
🔄 BUSINESS SWITCH — $PERSONA

Pre-conditions met (warmup ≥ 7 days). Manual steps required:

1. Open IG mobile app → Settings → Account
2. "Switch to Professional Account" → Business → category "Personal Blog" or "Public Figure"
3. Connect to Facebook → "Don't connect to Facebook now" if no FB Page yet
4. (Dais hand-action) Create matching FB Page:
   - facebook.com/pages/create
   - Page name = "@$PERSONA on Instagram" or similar
   - Category: Personal Blog
   - DO NOT post anything to FB Page yet
5. (In IG Settings) Re-connect to Facebook → select the new FB Page
6. Save IDs:
   - ig_business_account_id (visible in IG Settings → Business Tools)
   - fb_page_id (visible in FB Page Settings → About)
7. Update ~/anicca-monk-factory/accounts/$PERSONA/instagram.json:
   {"type":"business","fb_page_id":"...","ig_business_account_id":"...","status":"ready"}
8. (Postiz UI) Add IG Business + FB Page connections:
   - Postiz → Integrations → "Add Instagram" → select your FB Page
   - Postiz → Integrations → "Add Facebook" → select same FB Page
9. Add Postiz integration IDs to ~/anicca-monk-factory/.env:
   POSTIZ_${PERSONA//-/_}_IG_INTEGRATION=<id>
   POSTIZ_${PERSONA//-/_}_FB_INTEGRATION=<id>

After step 9, the persona is fully ready for daily posting via spawned factory cron.
EOF
