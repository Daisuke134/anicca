#!/usr/bin/env bash
set -uo pipefail
SOCK="/tmp/anicca-audit-tmux.sock"; SESSION="anicca-audit-core"
LOG="$HOME/.openclaw/logs/audit-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then echo "$(date '+%F %T') audit-core ALIVE" >> "$LOG"
else echo "$(date '+%F %T') audit-core DEAD → restart" >> "$LOG"; bash "$HOME/anicca/skills/earn/audit/audit-cli.sh" >> "$LOG" 2>&1 || true; fi
