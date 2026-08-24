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
  print -u2 "job-search browser: canonical home is unavailable"
  exit 1
fi
export HOME="$CANONICAL_HOME"

SCRIPT_DIR="${0:A:h}"
DISK_GUARD="${SCRIPT_DIR:h:h:h}/skills/earn/gig/scripts/gig_disk_guard.py"
if [[ ! -f "$DISK_GUARD" || -L "$DISK_GUARD" || ! -r "$DISK_GUARD" ]]; then
  print -u2 "job-search browser: disk guard is missing or unsafe"
  exit 1
fi

unset GIG_IGNORE_DISK_PRESSURE_BLOCK \
  GIG_IGNORE_DISK_WRITERS_STOP \
  DISK_CONTROL_STATE_DIR \
  OPENCLAW_STATE_DIR \
  LIFE_MANAGER_HOST_STATE_DIR
GIG_DISK_HEADROOM_KIB=524288
GIG_HOST_STATE_DIR="$CANONICAL_HOME/.openclaw/state"
GIG_STATE_DIR="$CANONICAL_HOME/.local/state/life-manager/job-search-browser"
export GIG_DISK_HEADROOM_KIB GIG_HOST_STATE_DIR GIG_STATE_DIR

if ! /usr/bin/python3 -I "$DISK_GUARD" /usr/bin/true; then
  print -u2 "job-search browser: disk guard blocked browser start"
  exit 1
fi

PROFILE="${JOB_SEARCH_BROWSER_PROFILE:-$HOME/.cloak/profiles/job-search-daily}"
mkdir -p "$PROFILE"
chmod 700 "$PROFILE"

CHROMIUM_BIN=$(ls -d "$HOME"/.cloakbrowser/chromium-*/Chromium.app/Contents/MacOS/Chromium(N) | sort -V | tail -1)
[[ -x "$CHROMIUM_BIN" ]] || {
  print -u2 "job-search browser: CloakBrowser Chromium is missing"
  exit 69
}

exec "$CHROMIUM_BIN" \
  --no-first-run \
  --no-default-browser-check \
  --password-store=basic \
  --use-mock-keychain \
  --disable-sync \
  --no-sandbox \
  --fingerprint=80137 \
  --fingerprint-platform=macos \
  --remote-debugging-address=127.0.0.1 \
  --remote-allow-origins='*' \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE" \
  about:blank
