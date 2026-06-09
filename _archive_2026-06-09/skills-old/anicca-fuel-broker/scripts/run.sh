#!/bin/bash
# anicca-fuel-broker entrypoint.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-fuel-broker"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== fuel-broker run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 60 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/broker.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
