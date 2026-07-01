#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# clip-healthcheck.sh — OS-level supervisor (launchd, every 5min). If the always-on clip-core
# tmux session is dead, restart it. Copied from Sutando's health-check-fallback role.
set -uo pipefail
SOCK="/tmp/anicca-clip-tmux.sock"; SESSION="anicca-clip-core"
LOG="$HOME/.openclaw/logs/clip-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "$(date '+%F %T') clip-core ALIVE" >> "$LOG"
else
  echo "$(date '+%F %T') clip-core DEAD → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/earn/clip/clip-cli.sh" >> "$LOG" 2>&1 || true
fi
