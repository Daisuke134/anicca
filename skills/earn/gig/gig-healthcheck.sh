#!/usr/bin/env bash
# gig-healthcheck.sh — launchd supervisor (5min). Restart the always-on gig-core if its tmux died.
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
LOG="$HOME/.openclaw/logs/gig-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "$(date '+%F %T') gig-core ALIVE" >> "$LOG"
else
  echo "$(date '+%F %T') gig-core DEAD → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/earn/gig/gig-cli.sh" >> "$LOG" 2>&1 || true
fi
