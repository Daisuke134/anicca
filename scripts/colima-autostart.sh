#!/bin/bash
# Keep the Docker runtime available only while disk-pressure backpressure is clear.
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

COLIMA_BIN="${COLIMA_AUTOSTART_BIN:-$(command -v colima || true)}"
DISK_PRESSURE_FLAG="${COLIMA_AUTOSTART_DISK_PRESSURE_FLAG:-$HOME/.openclaw/state/disk-pressure.block}"
LOG="${COLIMA_AUTOSTART_LOG:-$HOME/scripts/colima-autostart.log}"

mkdir -p "$(dirname "$LOG")"

if [ -e "$DISK_PRESSURE_FLAG" ]; then
  echo "$(date '+%F %T') disk pressure active — preserving stopped runtime" >> "$LOG"
  exit 0
fi

if [ -z "$COLIMA_BIN" ] || [ ! -x "$COLIMA_BIN" ]; then
  echo "$(date '+%F %T') colima binary missing — cannot autostart" >> "$LOG"
  exit 1
fi

if "$COLIMA_BIN" status >/dev/null 2>&1; then
  exit 0
fi

echo "$(date '+%F %T') colima not running, starting" >> "$LOG"
"$COLIMA_BIN" start >> "$LOG" 2>&1
status=$?
echo "$(date '+%F %T') colima start exit=$status" >> "$LOG"
exit "$status"
