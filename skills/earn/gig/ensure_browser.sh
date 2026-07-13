#!/usr/bin/env bash
# Bring the daily-driver browser back before the loop tries to use it.
#
# The loop drives Chromium over CDP :9222. When Chromium dies (it has: memory pressure from leaked
# tabs, GPU process exit_code=15) every pass afterwards is blind, and the external guard only ever
# relaunched it once. Self-healing belongs inside the loop, so the loop opens its own eyes at the
# start of every pass instead of waiting for something outside to notice.
#
#   bash ensure_browser.sh   -> prints ALIVE (already up) or RECOVERED (relaunched) or FAILED
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

CDP="http://127.0.0.1:9222"
PROFILE="$HOME/.cloak/profiles/daily-driver"
LOG="$HOME/.openclaw/logs/cdp-daily-driver-guard.log"

alive() { curl -s --max-time 4 "$CDP/json/version" >/dev/null 2>&1; }

if alive; then
  echo "ALIVE"
  exit 0
fi

# the real executable sits at <ver>/Chromium.app/Contents/MacOS/Chromium — five levels down
BIN=$(find "$HOME/.cloakbrowser" -maxdepth 6 -path "*/Contents/MacOS/Chromium" -type f 2>/dev/null | head -1)
if [ -z "$BIN" ]; then
  echo "FAILED: no Chromium binary under ~/.cloakbrowser"
  exit 1
fi

mkdir -p "$(dirname "$LOG")"
echo "$(date '+%F %T') ensure_browser: :9222 dead -> relaunching" >> "$LOG"
# Cap the caches. An uncapped profile grew to 1.0GB, of which 97% was Default/Cache and Code Cache;
# five such profiles filled the disk while the cookies that actually matter are a few hundred KB.
nohup "$BIN" --remote-debugging-port=9222 --user-data-dir="$PROFILE" \
  --disk-cache-size=104857600 --media-cache-size=52428800 --disable-gpu-shader-disk-cache \
  --no-first-run --no-default-browser-check >> "$LOG" 2>&1 &

for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if alive; then
    echo "$(date '+%F %T') ensure_browser: RECOVERED" >> "$LOG"
    echo "RECOVERED"
    exit 0
  fi
done

echo "$(date '+%F %T') ensure_browser: FAILED to recover" >> "$LOG"
echo "FAILED"
exit 1
