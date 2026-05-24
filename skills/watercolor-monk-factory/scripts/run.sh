#!/usr/bin/env bash
# Anicca Watercolor Factory — JP-only Kling watercolor pipeline (isshin copy)
# Usage: run.sh jp <slot> <postiz_integration_id>
set -euo pipefail
LANG_ARG="${1:?usage: run.sh jp <slot> <postiz_id>}"
SLOT="${2:?}"
POSTIZ_ID="${3:?}"

SKILL_DIR="$HOME/.openclaw/skills/watercolor-monk-factory/scripts"

echo "═══════════════════════════════════════════════"
echo "  Anicca Watercolor Factory — $LANG_ARG / $SLOT"
echo "  $(date)"
echo "═══════════════════════════════════════════════"

# Step 1: preflight
bash "$SKILL_DIR/preflight.sh" "$LANG_ARG"

# Step 2: rotate to next script
bash "$SKILL_DIR/rotate_script.sh" "$LANG_ARG"

# Step 3: generate video (Kling watercolor 13-scene)
FINAL=$(bash "$SKILL_DIR/generate.sh")
echo "🎥 produced: $FINAL"

# Step 4: post to TikTok+IG+YT
bash "$SKILL_DIR/post.sh" "$LANG_ARG" "$FINAL" "$POSTIZ_ID"

echo "═══════════════════════════════════════════════"
echo "  ✅ done $LANG_ARG / $SLOT"
echo "═══════════════════════════════════════════════"
