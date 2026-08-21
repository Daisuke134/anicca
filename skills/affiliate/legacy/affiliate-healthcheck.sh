#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # launchd has a minimal PATH; tmux/python3/node live in homebrew, claude itself lives in ~/.local/bin (npm global install, not homebrew)
# v2 (2026-07-04, タスク#7): pkill-by-name + backoff, ported from gig-healthcheck.sh —
# see clip-healthcheck.sh for the full incident writeup (tmux socket loss → duplicate
# cores → Load Avg 8.99 across 4 loops, real occurrence confirmed via `ps aux`).
# v4 (2026-07-04, self-heal-harness spec): mkdir atomic lock so overlapping healthcheck
# runs can't race each other's DEAD→restart sequence — see clip-healthcheck.sh for detail.
# v5 (2026-07-04, self-heal-harness spec): STALE detection (ported from gig-healthcheck.sh
# via clip-healthcheck.sh). affiliate cron runs once daily, so STALE_MIN=1560 (26h) —
# long enough that a single day's normal cron cadence never false-triggers.
# v6 (2026-07-08, incident): the STALE branch used to restart on EVERY healthcheck tick
# (every 300s via launchd) as long as $HB stayed old, with no regard for how recently the
# session had (re)started. Once HB went stale (e.g. daily cron didn't fire), each restart's
# fresh session got killed again 300s later — before producer.sh (slow PIL loop) or run.sh
# (browser posting, up to ~90s of confirmation polling) could ever finish and touch $HB.
# Confirmed via restart-log: dozens of restarts across Jul 6-8 with the queue growing
# (11 unposted decks) but nothing posted after Jun 30. Fix: give a freshly (re)started
# session a grace window (PASS_GRACE_MIN) to actually complete a pass before killing it again.
set -uo pipefail
SOCK="/tmp/anicca-affiliate-tmux.sock"; SESSION="anicca-affiliate-core"
HB="$HOME/.openclaw/state/.affiliate-core-last-pass"; START="$HOME/.openclaw/state/.affiliate-core-last-start"; STALE_MIN=1560; PASS_GRACE_MIN=20
LOG="$HOME/.openclaw/logs/affiliate-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.affiliate-core-restart-log"

LOCK_DIR="/tmp/.affiliate-healthcheck.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

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
    local task_file="$HOME/.openclaw/state/.affiliate-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"affiliate","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself, fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') ${1:-affiliate-core DEAD} → restart" >> "$LOG"
  bash "$HOME/profitable-claude/skills/affiliate/affiliate-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "affiliate-core DEAD"
elif [ ! -f "$HB" ]; then
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). Both "now" and epoch-0
    # fallbacks caused real incidents (now = STALE detection permanently disabled; epoch-0 =
    # immediate false restart of a healthy session). Don't guess: reseed the marker now and
    # let the NEXT healthcheck pass (5min later) measure from a real timestamp.
    touch "$START"
    echo "$(date '+%F %T') affiliate-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_MTIME="$(stat -f %m "$START")"
    START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "affiliate-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') affiliate-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))" -ge "$STALE_MIN" ]; then
  # HB is stale, but don't kill a session that might still be mid-pass: only restart if
  # it's ALSO been running since its last (re)start longer than a single pass should take.
  if [ -f "$START" ]; then
    START_AGE="$(( ($(date +%s) - $(stat -f %m "$START")) / 60 ))"
  else
    START_AGE=999999
  fi
  if [ "$START_AGE" -ge "$PASS_GRACE_MIN" ]; then
    restart "affiliate-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
  else
    echo "$(date '+%F %T') affiliate-core STALE-but-recent-start (started ${START_AGE}min ago, giving it ${PASS_GRACE_MIN}min grace)" >> "$LOG"
  fi
else
  echo "$(date '+%F %T') affiliate-core ALIVE+fresh" >> "$LOG"
fi
