#!/bin/zsh
set -euo pipefail

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
  --remote-debugging-port=0 \
  --user-data-dir="$PROFILE" \
  about:blank
