#!/usr/bin/env bash
# tiktok-account-factory — main orchestrator (Phase 4, scaffolded).
#
# Usage:
#   bash run.sh <persona-slug> <bio-url>
#
# Calls:
#   smspool-buy.sh → signup.sh → otp-relay.sh → ghost-mode.sh → (handoff to warmup-tiktok)
#
# Hardware preflight (Dais once per device, NOT automated): iPhone factory reset,
# US region, timezone NY/LA, location services OFF, Surfshark Dedicated IP added.
set -euo pipefail
PERSONA="${1:?persona-slug required (e.g. anicca-stoic)}"
BIO_URL="${2:?bio URL required (e.g. aniccaai.com/monk)}"

ROOT="$HOME/anicca-monk-factory"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
mkdir -p "$ACCOUNTS_DIR"

set -a; . "$ROOT/.env"; set +a

echo "═══════════════════════════════════════════════"
echo "  tiktok-account-factory — $PERSONA"
echo "  bio: $BIO_URL"
echo "═══════════════════════════════════════════════"

# Step 1: hardware preflight check
if [ ! -f "$ACCOUNTS_DIR/apple_id.json" ]; then
  cat <<EOF
🛑 HARDWARE PREFLIGHT — Dais must do this manually (once per device):
   1. Factory-reset iPhone 8/X/11
   2. Settings → General → Language & Region → United States
   3. Settings → General → Date & Time → OFF auto, set NY timezone
   4. Settings → Privacy & Security → Location Services → OFF (entirely)
   5. Connect Surfshark/NordVPN Dedicated IP (NY or LA)
   6. Insert Mint Mobile or Lycamobile US SIM (presence only)
   7. Create fresh Apple ID with US billing (Apple gift card \$30)
   8. Save Apple ID details to: $ACCOUNTS_DIR/apple_id.json
      Schema:
      {"{{profile.lateness.stakeholders.channel}}":"...","password":"...","phone":"+1...","billing_address":"...","region":"US","created_at":"YYYY-MM-DD"}

   Then re-run this script.
EOF
  exit 10
fi

# Step 2: SMSPool number purchase
[ -x "$SKILL_DIR/scripts/smspool-buy.sh" ] && bash "$SKILL_DIR/scripts/smspool-buy.sh" "$PERSONA" || { echo "❌ smspool-buy.sh failed"; exit 11; }

# Step 3: Playwright signup (TikTok phone-number flow)
[ -x "$SKILL_DIR/scripts/signup.sh" ] && bash "$SKILL_DIR/scripts/signup.sh" "$PERSONA" || { echo "❌ signup.sh failed"; exit 12; }

# Step 4: OTP relay (auto SMSPool poll → Slack fallback if no code in 90s)
[ -x "$SKILL_DIR/scripts/otp-relay.sh" ] && bash "$SKILL_DIR/scripts/otp-relay.sh" "$PERSONA" || { echo "❌ otp-relay.sh failed"; exit 13; }

# Step 5: Ghost mode (clear PFP/bio/link, scroll FYP for 15-20 min)
[ -x "$SKILL_DIR/scripts/ghost-mode.sh" ] && bash "$SKILL_DIR/scripts/ghost-mode.sh" "$PERSONA" || { echo "❌ ghost-mode.sh failed"; exit 14; }

# Handoff to warmup-tiktok
cat > "$ACCOUNTS_DIR/_next_step.md" <<EOF
# $PERSONA — TikTok account ready for 7-day warmup

Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Bio URL (apply after warmup): $BIO_URL

## Next step
\`\`\`
bash ~/.openclaw/skills/warmup-tiktok/scripts/run.sh $PERSONA
\`\`\`

After 7 days of warmup (algorithm trust signals + niche curation):
- Add PFP (locked avatar.png from spawned factory)
- Add bio
- Add bio link → $BIO_URL
- Connect Postiz: \`POSTIZ_${PERSONA//-/_}_TIKTOK_INTEGRATION=<id>\`
- Hand off to spawned factory for 3x/day cron posting
EOF

echo ""
echo "  ✅ TikTok account created for $PERSONA"
echo "  📋 Next step: $ACCOUNTS_DIR/_next_step.md"
echo "═══════════════════════════════════════════════"
