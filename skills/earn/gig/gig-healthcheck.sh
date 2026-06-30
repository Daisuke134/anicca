#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# gig-healthcheck.sh — launchd supervisor (5min). Two failure modes, both self-heal:
#   (1) DEAD: the tmux core died → restart it.
#   (2) STALE: the core is alive but the in-session :27 cron stopped firing (no pass in >90 min) →
#       restart it (a fresh start re-runs one pass + re-registers the cron). This closes the
#       continuity gap where the session lives but the internal scheduler silently stopped, so the
#       loop never wakes to reply to a buyer / catch a 仮払い. Heartbeat = ~/gig/.last-pass, touched
#       by the core at the start of every pass (see gig-cli.sh cron prompt).
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
HB="$HOME/gig/.last-pass"; STALE_MIN=90
LOG="$HOME/.openclaw/logs/gig-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
restart(){ echo "$(date '+%F %T') $1 → restarting" >> "$LOG"; bash "$HOME/anicca/skills/earn/gig/gig-cli.sh" --restart >> "$LOG" 2>&1 || true; }

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "gig-core DEAD"
elif [ ! -f "$HB" ]; then
  # FIND-001: alive but NO heartbeat = core started but never ran a pass (cron never registered/hung).
  # gig-cli seeds the heartbeat at startup, so a missing file means it never really booted → restart.
  restart "gig-core ALIVE but NO heartbeat (never fired)"
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB" 2>/dev/null || echo 0)) / 60 ))" -ge "$STALE_MIN" ]; then
  # FIND-005: -ge to match auditor's >=90 threshold exactly
  restart "gig-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') gig-core ALIVE+fresh" >> "$LOG"
fi
