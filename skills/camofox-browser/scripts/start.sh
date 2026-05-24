#!/usr/bin/env bash
# Start camofox-{{profile.lateness.stakeholders.channel}} server on :9377 if not running.
set -euo pipefail

CAMOFOX_DIR="$HOME/Developer/camofox-{{profile.lateness.stakeholders.channel}}"
LOG="/tmp/camofox.log"

if curl -sSf http://localhost:9377/health > /dev/null 2>&1; then
  echo "camofox already running"
  curl -sS http://localhost:9377/health
  exit 0
fi

if [ ! -d "$CAMOFOX_DIR" ]; then
  echo "ERROR: $CAMOFOX_DIR not found. clone https://github.com/jo-inc/camofox-{{profile.lateness.stakeholders.channel}} there first." >&2
  exit 1
fi

cd "$CAMOFOX_DIR"
nohup npm start > "$LOG" 2>&1 &
PID=$!
echo "started camofox pid=$PID, waiting..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 2
  if curl -sSf http://localhost:9377/health > /dev/null 2>&1; then
    curl -sS http://localhost:9377/health
    exit 0
  fi
done
echo "ERROR: camofox failed to start within 24s; see $LOG" >&2
tail -20 "$LOG" >&2
exit 1
