#!/usr/bin/env bash
# video-healthcheck.sh — OS-level supervisor (launchd, every 5min). If the always-on video-core
# tmux session is dead, restart it. Cloned from clip-healthcheck.sh so video is a real loop too.
set -uo pipefail
SOCK="/tmp/anicca-video-tmux.sock"; SESSION="anicca-video-core"
LOG="$HOME/.openclaw/logs/video-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "$(date '+%F %T') video-core ALIVE" >> "$LOG"
else
  echo "$(date '+%F %T') video-core DEAD → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/earn/video/video-cli.sh" >> "$LOG" 2>&1 || true
fi
