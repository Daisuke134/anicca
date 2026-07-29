#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude itself lives in ~/.local/bin (native installer, not homebrew)
# clip-promote-healthcheck.sh — OS-level supervisor (launchd, every 5min). If the always-on
# clip-promote-core tmux session is dead, restart it. Ported verbatim (v5 pattern) from
# clip-healthcheck.sh / gig-healthcheck.sh — same incidents, same fixes, applied up front instead
# of learned the hard way a second time:
#   (a) pkill by PROCESS NAME before restart — survives even when the tmux socket itself is gone
#   (b) backoff cap (max 5 restarts/60min) — stops a runaway restart loop from burning the Claude
#       subscription if the underlying cause recurs faster than we can fix it
#   (c) mkdir-based self-exclusion lock (macOS has no `flock`) — overlapping healthcheck runs can
#       never race each other's DEAD → pkill-then-restart sequence
#   (d) STALE detection — the tmux session can be ALIVE while the in-session internal cron has
#       stopped firing; a heartbeat file (touched only on a genuinely COMPLETED pass, never on
#       mere startup) catches this.
#
# STALE_MIN=250: clip-promote-cli.sh's internal cron fires every 2h (120min, promote.fun campaigns
# move slower than clip-rewards so a tighter cadence buys nothing). STALE_MIN must exceed one full
# internal-cron cycle with margin or this would false-restart every cycle; 250min ≈ 2x120min + 10min
# slack (same "≈2x the driving interval" ratio clip/gig use at their own cadence).
set -uo pipefail
SOCK="/tmp/anicca-clip-promote-tmux.sock"; SESSION="anicca-clip-promote-core"
HB="$HOME/.local/state/life-manager/state/.clip-promote-core-last-pass"; START="$HOME/.local/state/life-manager/state/.clip-promote-core-last-start"; STALE_MIN=250
LOG="$HOME/.local/state/life-manager/logs/clip-promote-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.local/state/life-manager/state/.clip-promote-core-restart-log"

# FIND-033 (2026-07-10, life-manager-loop 3-day outage; see healthcheck-lib.sh for the full
# writeup): under low free disk, macOS can't grow its swapfile and every fresh fork()/exec() on the
# box — including this script's own tmux+claude respawn — starts failing, so a DEAD session can
# restart-loop indefinitely even though the loop's own code is fine. That shared fix
# (hc_reclaim_disk_if_low) was applied to capafy/reddit/life-manager-loop via hc_run() but never
# ported to this standalone script, even though clip-promote-core-healthcheck.log shows the exact
# same signature (instant DEAD-after-restart, recurring for hours) since at least 2026-07-06.
# Source just the disk-reclaim helper (function defs only, no top-level side effects) so a restart
# always gets a real chance to fork.
# shellcheck source=$LIFE_MANAGER_REPO/skills/self/healthcheck-lib.sh
source "$LIFE_MANAGER_REPO/skills/self/healthcheck-lib.sh" 2>/dev/null || true

LOCK_DIR="/tmp/.clip-promote-healthcheck.lock"
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
    # self-heal-harness spec: give-up = the monitor layer can't fix this by restarting alone.
    # Write a task file instead of just logging — the NEXT time this loop's own claude-p core
    # wakes (next internal cron tick), its STARTUP prompt tells it to read this file and
    # diagnose/fix itself (or file a self/issue-dev issue if it can't). No human, no Opus, no
    # dev-Claude-Code session reads this — only the loop itself.
    local task_file="$HOME/.local/state/life-manager/state/.clip-promote-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"clip-promote","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself (check logs, run the failing command manually), fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  command -v hc_reclaim_disk_if_low >/dev/null 2>&1 && hc_reclaim_disk_if_low
  command -v hc_reap_stale_cozempic_guards >/dev/null 2>&1 && hc_reap_stale_cozempic_guards
  sleep 1
  echo "$(date '+%F %T') ${1:-clip-promote-core DEAD} → restarting" >> "$LOG"
  bash "$LIFE_MANAGER_REPO/skills/earn/clip-promote/clip-promote-cli.sh" --restart >> "$LOG" 2>&1 || true
}

HB_MTIME="$(stat -f %m "$HB" 2>/dev/null || echo 0)"
START_MTIME_CHECK="$(stat -f %m "$START" 2>/dev/null || echo 0)"

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "clip-promote-core DEAD"
elif [ ! -f "$HB" ] || [ "$HB_MTIME" -lt "$START_MTIME_CHECK" ]; then
  # No completed pass yet UNDER THE CURRENT SESSION -- either $HB was never written, or it's a
  # leftover from a PRIOR session (its mtime predates this session's $START marker). Either way
  # this is NOT evidence of staleness; use the post-restart grace window instead of comparing
  # $HB's raw age. (2026-07-11 incident: a freshly-restarted, actively-working session was killed
  # mid-flight because the pre-restart $HB was days-stale and this branch only special-cased a
  # totally-ABSENT $HB, not a stale-but-present one that predated the restart.)
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). Both "now" and epoch-0
    # fallbacks caused real incidents (now = STALE detection permanently disabled; epoch-0 =
    # immediate false restart of a healthy session). Don't guess: reseed the marker now and
    # let the NEXT healthcheck pass (5min later) measure from a real timestamp.
    touch "$START"
    echo "$(date '+%F %T') clip-promote-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_AGE="$(( ($(date +%s) - START_MTIME_CHECK) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "clip-promote-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') clip-promote-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif [ "$(( ($(date +%s) - HB_MTIME) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "clip-promote-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') clip-promote-core ALIVE+fresh" >> "$LOG"
fi
