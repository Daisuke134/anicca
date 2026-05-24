#!/usr/bin/env bash
# Single entrypoint for cron — dumb-model-friendly.
# Usage: run.sh <en|jp> <slot> <postiz_integration_id>
# All assets are LOCKED — this script only generates one new video and posts it.
set -euo pipefail
LANG_ARG="${1:?usage: run.sh <en|jp> <slot> <postiz_id>}"
SLOT="${2:?}"
POSTIZ_ID="${3:?}"

SKILL_DIR="$HOME/.openclaw/skills/yangmun-monk-factory/scripts"

echo "═══════════════════════════════════════════════"
echo "  Anicca Monk Factory — $LANG_ARG / $SLOT"
echo "  $(date)"
echo "═══════════════════════════════════════════════"

# Step 1: preflight
bash "$SKILL_DIR/preflight.sh" "$LANG_ARG"

# Step 2: rotate to next script
bash "$SKILL_DIR/rotate_script.sh" "$LANG_ARG"

# Step 3: generate video
case "$LANG_ARG" in
  en) FINAL=$(bash "$SKILL_DIR/generate_en.sh") ;;
  jp) FINAL=$(bash "$SKILL_DIR/generate_jp.sh") ;;
esac
echo "🎥 produced: $FINAL"

# Step 4: post to TikTok
bash "$SKILL_DIR/post.sh" "$LANG_ARG" "$FINAL" "$POSTIZ_ID"

echo "═══════════════════════════════════════════════"
echo "  ✅ done $LANG_ARG / $SLOT"
echo "═══════════════════════════════════════════════"
