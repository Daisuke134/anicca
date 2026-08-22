#!/bin/zsh
set -euo pipefail

if ! CANONICAL_HOME="$(/usr/bin/python3 -I - <<'PY'
import os
import pwd
import sys

try:
    home = pwd.getpwuid(os.getuid()).pw_dir
except (KeyError, OSError):
    raise SystemExit(1)
if not isinstance(home, str) or not os.path.isabs(home) or not os.path.isdir(home):
    raise SystemExit(1)
sys.stdout.write(home)
PY
)"; then
  print -u2 "mercor browser: canonical home is unavailable"
  exit 1
fi
export HOME="$CANONICAL_HOME"

DISK_GUARD="$HOME/gig/releases/life-manager/current/skills/earn/gig/scripts/gig_disk_guard.py"
if [[ ! -f "$DISK_GUARD" || -L "$DISK_GUARD" || ! -r "$DISK_GUARD" ]]; then
  print -u2 "mercor browser: disk guard is missing or unsafe"
  exit 1
fi

unset GIG_IGNORE_DISK_PRESSURE_BLOCK \
  GIG_IGNORE_DISK_WRITERS_STOP \
  DISK_CONTROL_STATE_DIR \
  OPENCLAW_STATE_DIR \
  LIFE_MANAGER_HOST_STATE_DIR
GIG_DISK_HEADROOM_KIB=524288
GIG_HOST_STATE_DIR="$HOME/.openclaw/state"
GIG_STATE_DIR="$HOME/.local/state/life-manager/mercor-browser"
export GIG_DISK_HEADROOM_KIB GIG_HOST_STATE_DIR GIG_STATE_DIR

if ! /usr/bin/python3 -I "$DISK_GUARD" /usr/bin/true; then
  print -u2 "mercor browser: disk guard blocked browser start"
  exit 1
fi

: "${JOB_SEARCH_MERCOR_BROWSER_PROFILE:?JOB_SEARCH_MERCOR_BROWSER_PROFILE is required}"
: "${JOB_SEARCH_MERCOR_CHROMIUM:?JOB_SEARCH_MERCOR_CHROMIUM is required}"
: "${JOB_SEARCH_MERCOR_BROWSER_PORT:?JOB_SEARCH_MERCOR_BROWSER_PORT is required}"

PROFILE="$JOB_SEARCH_MERCOR_BROWSER_PROFILE"
CHROMIUM_BIN="$JOB_SEARCH_MERCOR_CHROMIUM"
PORT="$JOB_SEARCH_MERCOR_BROWSER_PORT"

if [[ "$PROFILE" != /* || ! -d "$PROFILE" || ! -r "$PROFILE" ]]; then
  print -u2 "mercor browser: profile must be an absolute readable directory"
  exit 64
fi
if [[ "$CHROMIUM_BIN" != /* || ! -f "$CHROMIUM_BIN" || ! -x "$CHROMIUM_BIN" ]]; then
  print -u2 "mercor browser: Chromium must be an absolute executable file"
  exit 69
fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
  print -u2 "mercor browser: port must be an integer from 1 through 65535"
  exit 64
fi

if ! /usr/bin/pgrep -f -- "--user-data-dir=$PROFILE" >/dev/null 2>&1; then
  /bin/rm -f "$PROFILE/SingletonLock" "$PROFILE/SingletonSocket" "$PROFILE/SingletonCookie"
fi

exec "$CHROMIUM_BIN" \
  --no-first-run \
  --no-default-browser-check \
  --no-sandbox \
  --password-store=basic \
  --use-mock-keychain \
  --disable-sync \
  --disk-cache-size=104857600 \
  --media-cache-size=52428800 \
  --fingerprint=81234 \
  --fingerprint-platform=macos \
  --remote-debugging-address=127.0.0.1 \
  --remote-allow-origins='*' \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  about:blank
