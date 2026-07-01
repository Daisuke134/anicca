#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
set -uo pipefail
SOCK="/tmp/anicca-bounty-tmux.sock"; SESSION="anicca-bounty-core"
LOG="$HOME/.openclaw/logs/bounty-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then echo "$(date '+%F %T') bounty-core ALIVE" >> "$LOG"
else echo "$(date '+%F %T') bounty-core DEAD → restart" >> "$LOG"; bash "$HOME/anicca/skills/earn/bounty/bounty-cli.sh" >> "$LOG" 2>&1 || true; fi
