#!/usr/bin/env bash
set -euo pipefail
browser="${LANCERS_CHROMIUM:-}"
if [ -z "$browser" ]; then
  browser="$(find "$HOME/.cloakbrowser" -maxdepth 4 -type f -path '*/Chromium.app/Contents/MacOS/Chromium' -print 2>/dev/null | sort | tail -1)"
fi
[ -x "$browser" ] || { echo "lancers browser binary unavailable" >&2; exit 78; }
profile="${LANCERS_BROWSER_PROFILE:-$HOME/.local/state/anicca/lancers/browser-profile}"
mkdir -p "$profile"
exec "$browser" --no-first-run --no-default-browser-check \
  --remote-debugging-address=127.0.0.1 --remote-allow-origins='*' \
  --remote-debugging-port=9227 --user-data-dir="$profile" about:blank
