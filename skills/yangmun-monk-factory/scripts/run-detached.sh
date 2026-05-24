#!/usr/bin/env bash
# Detached wrapper for run.sh — fire and forget so cron agent (gpt-5.4-mini)
# can return immediately. The actual generation runs in a new process group
# (setsid) so it survives the agent session ending.
#
# Usage: run-detached.sh <en|jp> <slot> <postiz_integration_id>
set -euo pipefail
LANG_ARG="${1:?usage: run-detached.sh <en|jp> <slot> <postiz_id>}"
SLOT="${2:?}"
POSTIZ_ID="${3:?}"

ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/run_${LANG_ARG}_${SLOT}_${TS}.log"
mkdir -p "$ROOT/state"

# Launch detached in a macOS-safe way
nohup bash "$HOME/.openclaw/skills/yangmun-monk-factory/scripts/run.sh" \
  "$LANG_ARG" "$SLOT" "$POSTIZ_ID" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ kicked off run.sh PID=$PID lang=$LANG_ARG slot=$SLOT"
echo "   log: $LOG"
echo "   The cron agent can now exit; the render continues in the background."
