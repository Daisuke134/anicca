#!/usr/bin/env bash
# instagram-account-factory — main orchestrator (Phase 4, scaffolded).
set -euo pipefail
PERSONA="${1:?persona required}"
BIO_URL="${2:?bio URL required}"

ROOT="$HOME/anicca-monk-factory"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
mkdir -p "$ACCOUNTS_DIR"
set -a; . "$ROOT/.env"; set +a

echo "═══════════════════════════════════════════════"
echo "  instagram-account-factory — $PERSONA"
echo "  bio: $BIO_URL"
echo "═══════════════════════════════════════════════"

# Step 1: pre-flight — TT account must exist (shares Apple ID + device)
if [ ! -f "$ACCOUNTS_DIR/apple_id.json" ]; then
  echo "🛑 No apple_id.json — run tiktok-account-factory FIRST (it creates Apple ID + ghost mode)"
  exit 41
fi
if [ ! -f "$ACCOUNTS_DIR/tiktok.json" ]; then
  echo "🛑 No tiktok.json — run tiktok-account-factory first"
  exit 42
fi

# Step 2: IG Personal signup (Playwright, phone-number flow)
[ -x "$SKILL_DIR/scripts/signup-personal.sh" ] && bash "$SKILL_DIR/scripts/signup-personal.sh" "$PERSONA" || { echo "❌ signup-personal failed"; exit 43; }

# Step 3: hand off to warmup-instagram
echo ""
echo "  ✅ IG Personal account created. Handing off to 7-day warmup."
cat > "$ACCOUNTS_DIR/_ig_next_step.md" <<EOF
# $PERSONA — IG Personal account ready for 7-day warmup

Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Next step (auto, after 7 days)

\`\`\`
bash ~/.openclaw/skills/warmup-instagram/scripts/run.sh $PERSONA
\`\`\`

## After warmup completes (7 days)

\`\`\`
bash ~/.openclaw/skills/instagram-account-factory/scripts/business-switch.sh $PERSONA
\`\`\`

This switches Personal → Business and prompts Dais to:
  1. Create matching FB Page (Dais hand-action)
  2. Link IG to FB Page (in IG Settings)
  3. Add to Postiz: IG Business + FB Page IDs

## Then Postiz integration

Add to ~/anicca-monk-factory/.env:
  POSTIZ_${PERSONA//-/_}_IG_INTEGRATION=<id from Postiz UI>
  POSTIZ_${PERSONA//-/_}_FB_INTEGRATION=<id from Postiz UI>

Bio link (apply via mobile IG app, after warmup): $BIO_URL
EOF

echo "  📋 Next step: $ACCOUNTS_DIR/_ig_next_step.md"
echo "═══════════════════════════════════════════════"
