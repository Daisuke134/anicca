#!/bin/bash
# anicca-goal-learner entrypoint — weekly proactive goal-drift report.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-goal-learner"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== goal-learner run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/learner.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
