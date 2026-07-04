#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# clip-healthcheck.sh — OS-level supervisor (launchd, every 5min). If the always-on clip-core
# tmux session is dead, restart it. Copied from Sutando's health-check-fallback role.
#
# v2 (2026-07-04, タスク#7): tmux socket loss (root cause still under investigation) made
# `has-session` return false-DEAD while the underlying claude process was still alive,
# so a new session got started ON TOP of it. Across 4 loops this piled up to 8 processes
# per loop over ~12h and pushed Load Avg to 8.99 (real incident, confirmed via `ps aux`).
# Fix, ported from gig-healthcheck.sh's proven pattern:
#   (a) pkill by PROCESS NAME before restart — survives even when the socket itself is gone
#   (b) backoff cap (max 5 restarts/60min) — stops a runaway restart loop from burning the
#       Claude subscription if the underlying cause recurs faster than we can fix it
#
# NOTE (2026-07-04, same session): an "also reap orphans on every ALIVE check" v3 attempt
# was tried and REVERTED — both a pane_pid-based and a newest-by-start-time heuristic each
# ended up killing the one genuinely live process (verified: session went from ALIVE to
# "no server running" right after a reap). Auto-detecting "which of N same-named processes
# is the real one" from outside is unreliable; do not re-add without a verified-safe method.
# Existing orphans from past incidents must be cleaned up MANUALLY (`ps aux | grep`, compare
# start times, kill all but the one attached to `tmux ... list-sessions`) — see Task #7.
set -uo pipefail
SOCK="/tmp/anicca-clip-tmux.sock"; SESSION="anicca-clip-core"
LOG="$HOME/.openclaw/logs/clip-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.clip-core-restart-log"

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
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting (likely persistent failure)" >> "$LOG"
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') clip-core DEAD → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/earn/clip/clip-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  echo "$(date '+%F %T') clip-core ALIVE" >> "$LOG"
else
  restart
fi
