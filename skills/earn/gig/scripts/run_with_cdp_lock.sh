#!/usr/bin/env bash
# Run one browser-driving child while holding the same lock as the gig auditor.
# The child never attaches to an existing tab by itself; the caller's prompt must
# open/close a self-owned persistent default tab while this lease is held.
set -uo pipefail

if [ "$#" -lt 4 ] || [ "$3" != "--" ]; then
  echo "usage: $0 OWNER TIMEOUT -- COMMAND [ARGS...]" >&2
  exit 64
fi

OWNER="$1"
TIMEOUT="$2"
shift 3
if [ "${GIG_CDP_LOCK_HELD:-0}" = 1 ]; then
  "$@"
  exit $?
fi
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/cdp_lock.sh"
if ! cdp_lock_acquire "$OWNER" "$TIMEOUT"; then
  echo "deferred_cdp_busy" >&2
  exit 75
fi
HEARTBEAT_SECS="${CDP_LOCK_HEARTBEAT_SECS:-30}"
case "$HEARTBEAT_SECS" in
  ''|*[!0-9]*|0) echo "invalid CDP_LOCK_HEARTBEAT_SECS" >&2; cdp_lock_release; exit 64 ;;
esac
HEARTBEAT_PID=""
python3 - "$$" "$CDP_LOCK_DIR/meta" "$HEARTBEAT_SECS" >/dev/null 2>&1 <<'PY' &
import os
import sys
import time

parent, meta, interval = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
while True:
    time.sleep(interval)
    try:
        os.kill(parent, 0)
    except OSError:
        raise SystemExit(0)
    try:
        os.utime(meta)
    except OSError:
        raise SystemExit(0)
PY
HEARTBEAT_PID=$!
cleanup() {
  [ -n "$HEARTBEAT_PID" ] && kill "$HEARTBEAT_PID" 2>/dev/null || true
  [ -n "$HEARTBEAT_PID" ] && wait "$HEARTBEAT_PID" 2>/dev/null || true
  cdp_lock_release
}
trap cleanup EXIT HUP INT TERM

export GIG_CDP_LOCK_HELD=1
"$@"
RC=$?
exit "$RC"
