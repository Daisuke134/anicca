#!/usr/bin/env bash
# youtube-account-factory — main orchestrator (Phase 4, scaffolded)
set -euo pipefail
PERSONA="${1:?persona required}"

ROOT="$HOME/anicca-monk-factory"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
GMAILS_REGISTRY="$ROOT/accounts/_gmails_registry.json"

mkdir -p "$ACCOUNTS_DIR"
set -a; . "$ROOT/.env"; set +a

echo "═══════════════════════════════════════════════"
echo "  youtube-account-factory — $PERSONA"
echo "═══════════════════════════════════════════════"

[ -f "$ACCOUNTS_DIR/apple_id.json" ] || { echo "🛑 No apple_id.json — run tiktok-account-factory first"; exit 71; }

# Pick a Gmail with capacity (< 6 Brand Accounts under it)
GMAIL=$(python3 -c "
import json, os
reg_path = '$GMAILS_REGISTRY'
if not os.path.exists(reg_path):
    json.dump({'gmails': []}, open(reg_path, 'w'))
reg = json.load(open(reg_path))
for g in reg.get('gmails', []):
    if len(g.get('brand_accounts', [])) < 6:
        print(g['{{profile.lateness.stakeholders.channel}}']); break
else:
    print('')
")

if [ -z "$GMAIL" ]; then
  echo "🛑 No Gmail with capacity (< 6 Brand Accounts). Dais must create a fresh Gmail:"
  echo "    bash $SKILL_DIR/scripts/gmail-signup.sh"
  echo "  Then re-run this script."
  exit 72
fi

echo "  📧 using Gmail: $GMAIL (under 6 Brand Account limit)"

# Step 3: Brand Account create
[ -x "$SKILL_DIR/scripts/brand-account-create.sh" ] && \
  bash "$SKILL_DIR/scripts/brand-account-create.sh" "$PERSONA" "$GMAIL" || { echo "❌ brand-account-create failed"; exit 73; }

# Step 4: Channel customize
[ -x "$SKILL_DIR/scripts/channel-customize.sh" ] && \
  bash "$SKILL_DIR/scripts/channel-customize.sh" "$PERSONA" || true

# Step 5: handoff
cat > "$ACCOUNTS_DIR/_yt_next_step.md" <<EOF
# $PERSONA — YouTube channel ready

Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Gmail: $GMAIL

## Next step (manual, ~5 min)

1. Open Postiz UI → Integrations → "Add YouTube"
2. Sign in with $GMAIL → select Brand Account for @$PERSONA
3. Authorize all scopes (upload, read stats)
4. Copy integration ID from Postiz UI
5. Add to ~/anicca-monk-factory/.env:
   POSTIZ_${PERSONA//-/_}_YT_INTEGRATION=<id>

## Then run warmup (lighter than TT/IG)

\`\`\`
bash ~/.openclaw/skills/warmup-youtube/scripts/run.sh $PERSONA
\`\`\`

## After warmup (1-2 days)

Channel is ready for spawned factory cron posting via Postiz.
EOF

echo "  ✅ YouTube channel created. Next step: $ACCOUNTS_DIR/_yt_next_step.md"
echo "═══════════════════════════════════════════════"
