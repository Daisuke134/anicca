#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# v2 (2026-07-04, タスク#7): pkill-by-name + backoff, ported from gig-healthcheck.sh —
# see clip-healthcheck.sh for the full incident writeup (tmux socket loss → duplicate
# cores → Load Avg 8.99 across 4 loops, real occurrence confirmed via `ps aux`).
set -uo pipefail
SOCK="/tmp/anicca-bounty-tmux.sock"; SESSION="anicca-bounty-core"
LOG="$HOME/.openclaw/logs/bounty-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.bounty-core-restart-log"

restart() {
  mkdir -p "$HOME/.openclaw/state"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting" >> "$LOG"
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') bounty-core DEAD → restart" >> "$LOG"
  bash "$HOME/anicca/skills/earn/bounty/bounty-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "$(date '+%F %T') bounty-core ALIVE" >> "$LOG"
else
  restart
fi
