#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
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
#
# v4 (2026-07-04, self-heal-harness spec, Sutando+Cronicle patterns): add a self-exclusion
# lock so overlapping healthcheck runs (launchd firing before the prior run finished) can
# never race each other's DEAD→pkill-then-restart sequence — this race is a strong
# candidate for HOW the v2 pkill-by-name still let duplicates through. macOS has no
# `flock` binary (confirmed absent, unlike Linux), so this uses mkdir as an atomic lock
# (same proven pattern as ~/scripts/disk-cleaner.sh's LOCK_DIR).
#
# v5 (2026-07-04, self-heal-harness spec): STALE detection, ported verbatim from
# gig-healthcheck.sh (the one loop that never suffered a duplicate-pile-up). Detects
# "tmux session alive but the in-session hourly cron stopped firing" via a heartbeat
# file the cron prompt touches only on a genuinely COMPLETED pass (clip-cli.sh STARTUP
# now does `FINALLY touch .clip-core-last-pass`). STALE_MIN=90 matches clip's hourly
# cadence (gig uses the same 90min for its hourly cadence too).
set -uo pipefail
SOCK="/tmp/anicca-clip-tmux.sock"; SESSION="anicca-clip-core"
HB="$HOME/.local/state/life-manager/state/.clip-core-last-pass"; START="$HOME/.local/state/life-manager/state/.clip-core-last-start"; STALE_MIN=90
LOG="$HOME/.local/state/life-manager/logs/clip-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.local/state/life-manager/state/.clip-core-restart-log"

LOCK_DIR="/tmp/.clip-healthcheck.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0   # a prior healthcheck run is still in flight — skip silently, don't race it
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

restart() {
  mkdir -p "$HOME/.local/state/life-manager/state"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting (likely persistent failure)" >> "$LOG"
    # self-heal-harness spec: give-up = the monitor layer can't fix this by restarting
    # alone. Write a task file instead of just logging — the NEXT time this loop's
    # own claude-p core wakes (next cron tick), its STARTUP prompt tells it to read
    # this file and diagnose/fix itself (or file a self/issue-dev issue if it can't).
    # No human, no Opus, no dev-Claude-Code session reads this — only the loop itself.
    local task_file="$HOME/.local/state/life-manager/state/.clip-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"clip","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself (check logs, run the failing command manually), fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') ${1:-clip-core DEAD} → restarting" >> "$LOG"
  bash "$LIFE_MANAGER_REPO/skills/earn/clip/clip-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "clip-core DEAD"
elif [ ! -f "$HB" ]; then
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). Both "now" and epoch-0
    # fallbacks caused real incidents (now = STALE detection permanently disabled; epoch-0 =
    # immediate false restart of a healthy session). Don't guess: reseed the marker now and
    # let the NEXT healthcheck pass (5min later) measure from a real timestamp. A genuinely
    # stuck session is still caught within STALE_MIN of this reseed.
    touch "$START"
    echo "$(date '+%F %T') clip-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_MTIME="$(stat -f %m "$START")"
    START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "clip-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') clip-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "clip-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') clip-core ALIVE+fresh" >> "$LOG"
fi
