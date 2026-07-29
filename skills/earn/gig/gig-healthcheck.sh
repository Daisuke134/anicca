#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# gig-healthcheck.sh — launchd supervisor (5min). Two failure modes, both self-heal:
#   (1) DEAD: the tmux core died → restart it.
#   (2) STALE: the provider-free core supervisor stopped heartbeating. The OS-owned
#       ai.anicca.hf-gig-pass LaunchAgent schedules actual passes at Minute=27.
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
HB="$HOME/gig/.gig-core-heartbeat"; STALE_MIN=5
LOG="$HOME/.openclaw/logs/gig-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/gig/.restart-log"
DOCKER_DISK_PRESSURE_FLAG="${GIG_DOCKER_DISK_PRESSURE_FLAG:-$HOME/.openclaw/state/disk-pressure.block}"
restart(){
  # backoff: max 5 restarts per 60min window (prevent subscription drain under persistent failure)
  mkdir -p "$HOME/gig"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting (likely quota/persistent failure; will resume after reset)" >> "$LOG"
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  echo "$(date '+%F %T') $1 → restarting" >> "$LOG"
  bash "$HOME/profitable-claude/skills/gig-work/gig-cli.sh" --restart >> "$LOG" 2>&1 || true
}

# Docker sandbox self-heal (observed live 2026-07-25: colima down killed paid-work
# validation for 14 straight passes, then a recreated VM lost the sandbox image).
# Daemon down → colima start. Image missing → rebuild from the official openclaw recipe.
docker_selfheal() {
  local docker_bin pressure_active=0 pressure_free_gb=""
  if [ -e "$DOCKER_DISK_PRESSURE_FLAG" ]; then
    pressure_active=1
    pressure_free_gb=$(awk '{
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^free_gb=[0-9]+$/) {
          sub(/^free_gb=/, "", $i)
          print $i
          exit
        }
      }
    }' "$DOCKER_DISK_PRESSURE_FLAG" 2>/dev/null || true)
    case "$pressure_free_gb" in
      ''|*[!0-9]*)
        echo "$(date '+%F %T') disk pressure active — preserving stopped Docker runtime (free space unreadable)" >> "$LOG"
        return
        ;;
    esac
    if [ "$pressure_free_gb" -lt "${GIG_DOCKER_MIN_REBUILD_FREE_GB:-5}" ]; then
      echo "$(date '+%F %T') disk pressure active — preserving stopped Docker runtime (${pressure_free_gb}GB free)" >> "$LOG"
      return
    fi
  fi
  docker_bin=$(command -v docker || true)
  [ -n "$docker_bin" ] || { echo "$(date '+%F %T') docker binary missing — cannot self-heal sandbox" >> "$LOG"; return; }
  if ! "$docker_bin" info > /dev/null 2>&1; then
    if [ "$pressure_active" -eq 1 ]; then
      echo "$(date '+%F %T') disk pressure active — preserving stopped Docker runtime (${pressure_free_gb}GB free)" >> "$LOG"
      return
    fi
    echo "$(date '+%F %T') docker daemon DOWN → colima start" >> "$LOG"
    colima start >> "$LOG" 2>&1 || { echo "$(date '+%F %T') colima start FAILED" >> "$LOG"; return; }
  fi
  if ! "$docker_bin" image inspect openclaw-sandbox:bookworm-slim > /dev/null 2>&1; then
    echo "$(date '+%F %T') sandbox image missing → rebuilding" >> "$LOG"
    "$docker_bin" build -t openclaw-sandbox:bookworm-slim - >> "$LOG" 2>&1 <<'DOCKERFILE' || echo "$(date '+%F %T') sandbox image rebuild FAILED" >> "$LOG"
FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
  bash ca-certificates curl git jq python3 ripgrep \
  && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
CMD ["sleep", "infinity"]
DOCKERFILE
  fi
}
docker_selfheal

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "gig-core DEAD"
elif [ ! -f "$HB" ] || [ "$HB" -ot "$HOME/gig/.last-start" ]; then
  START_AGE="$(( ($(date +%s) - $(stat -f %m "$HOME/gig/.last-start" 2>/dev/null || echo 0)) / 60 ))"
  if [ "$START_AGE" -ge "$STALE_MIN" ]; then
    restart "gig-core ALIVE but supervisor heartbeat missing for >=${START_AGE}min"
  else
    echo "$(date '+%F %T') gig-core ALIVE (supervisor heartbeat pending, ${START_AGE}min since start)" >> "$LOG"
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB" 2>/dev/null || echo 0)) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "gig-core STALE (no supervisor heartbeat in >=${STALE_MIN}min)"
else
  echo "$(date '+%F %T') gig-core ALIVE+fresh" >> "$LOG"
fi
