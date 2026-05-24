#!/usr/bin/env bash
# Customize the new YouTube channel: profile pic, banner, description.
# Pulls assets from the spawned factory's avatar.png + clone_spec_meta.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"

# Find the spawned factory matching this persona slug
SKILL_PERSONA_DIR="$HOME/.openclaw/skills/${PERSONA}-factory"
[ -d "$SKILL_PERSONA_DIR" ] || { echo "ℹ no spawned factory at $SKILL_PERSONA_DIR — skip customize"; exit 0; }

AVATAR="$SKILL_PERSONA_DIR/assets/avatar.png"
[ -f "$AVATAR" ] || { echo "ℹ no avatar.png in spawned skill — skip"; exit 0; }

cat <<EOF
🛠 STUB: channel-customize.sh — Playwright spec not yet implemented.

Persona: $PERSONA
Avatar source: $AVATAR

Implementation reference:
1. Playwright login → studio.youtube.com → channel customization
2. Upload \$AVATAR as profile picture (will be cropped to circle)
3. Generate banner via fal flux (16:9 wide) using clone_spec.avatar.fal_flux_prompt
4. Set channel description from clone_spec.hook_pattern + bio link → aniccaai.com/<lang>
EOF
exit 0
