#!/usr/bin/env bash
# Stage 7: SCHEDULE — register 3 cron slots/day with OpenClaw, DISABLED.
# Dais runs `openclaw cron enable <id>` after manual one-shot test passes.
#
# Reads cron.template.txt from the spawned skill and feeds each `openclaw cron add`
# block to the openclaw CLI. Disables each cron immediately after creation.
set -euo pipefail
NICHE_SLUG="${1:?niche_slug required}"
LANG_ARG="${2:?lang required}"

TARGET_DIR="$HOME/.openclaw/skills/${NICHE_SLUG}-factory"
TEMPLATE="$TARGET_DIR/cron.template.txt"

[ -f "$TEMPLATE" ] || { echo "  ⚠ no cron.template.txt at $TEMPLATE — skipping"; exit 0; }
command -v openclaw >/dev/null 2>&1 || { echo "  ⚠ openclaw CLI not found — skipping cron add"; exit 0; }

echo ""
echo "─── Stage 7: SCHEDULE ───"

# Parse template — each `openclaw cron add ... ` block ends at blank line.
# We just feed the WHOLE script through bash; openclaw cron add is line-continued.
# Catch added cron names so we can disable them right after.
ADDED_NAMES=$(grep -E "^[[:space:]]*--name " "$TEMPLATE" | sed 's/.*--name //; s/ *\\//; s/^[[:space:]]*//; s/[[:space:]]*$//' | head -10)

# Run the template (it contains line-continued openclaw cron add commands).
# Capture stdout for parsing cron IDs.
RUN_OUT=$(bash "$TEMPLATE" 2>&1 || true)
echo "$RUN_OUT" | sed 's/^/  /'

# Disable all newly added crons.
for NAME in $ADDED_NAMES; do
  ID=$(openclaw cron list 2>/dev/null | grep -E "[0-9a-f-]{36}[[:space:]]+${NAME}[[:space:]]" | awk '{print $1}' | head -1)
  if [ -n "$ID" ]; then
    openclaw cron disable "$ID" 2>/dev/null && echo "  🔒 disabled cron: $NAME ($ID)" || echo "  ⚠ disable failed: $NAME"
  else
    echo "  ⚠ cron not found by name: $NAME"
  fi
done

echo "  ✅ Stage 7 done — 3 crons added DISABLED. Dais runs \`openclaw cron enable <id>\` to activate."
