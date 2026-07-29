#!/usr/bin/env bash
# Stop camofox server (and its child Firefox)
#
# self-fix 2026-07-12: `npm start` runs `node server.js` with a plain relative argv (cwd is the
# camofox-browser dir, but the command line itself never contains the string "camofox-browser"),
# so `pkill -f "node.*camofox-browser"` NEVER matched the real process -- this script always
# printed "WARNING: camofox still running" and left the old (possibly browser-dead) process alive
# forever. Kill by the port it actually owns instead, which is unambiguous regardless of argv.
set -uo pipefail
LOCK_DIR="/tmp/camofox-browser-lifecycle.lock"

# Coordinate teardown with start.sh: an overlapping healthcheck must not reap
# a freshly detached server between its health probe and the first /tabs call.
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  owner="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then
    rm -f "$LOCK_DIR/pid" 2>/dev/null || true
    rmdir "$LOCK_DIR" 2>/dev/null || true
  else
    sleep 1
  fi
done
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null || true; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

PORT_PID="$(lsof -ti :9377 2>/dev/null || true)"
[ -n "$PORT_PID" ] && kill $PORT_PID 2>/dev/null || true
pkill -f "node.*camofox-browser" 2>&1 | head -3 || true
pkill -f "Camoufox.app" 2>&1 | head -3 || true
sleep 1
PORT_PID="$(lsof -ti :9377 2>/dev/null || true)"
if [ -n "$PORT_PID" ]; then
  kill -9 $PORT_PID 2>/dev/null || true
  sleep 1
fi
if curl -sSf --max-time 3 http://localhost:9377/health > /dev/null 2>&1; then
  echo "WARNING: camofox still running"
  exit 1
fi
echo "camofox stopped"
