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
  # A loop killed with -9 never releases its context, and an orphaned context keeps its tabs alive
  # forever. Every pass comes through here, so this is the one place a reaper cannot be forgotten.
  python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/cdp_context_lease.py" gc --idle-min 45 >/dev/null 2>&1 || true
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
# Cap the caches and move them off the profile. An uncapped profile grew to 1.0GB, of which 97% was
# Default/Cache and Code Cache; five of them crowded the disk the loops write their ledgers to, while
# the cookies that keep us logged in are only a few hundred KB.
# Flags verified against peter.sh/experiments/chromium-command-line-switches (--media-cache-size and
# --memory-pressure-off do not exist in current Chromium; do not add them back).
nohup "$BIN" --remote-debugging-port=9222 --user-data-dir="$PROFILE" \
  --disk-cache-size=209715200 --disk-cache-dir=/tmp/cloak-cache \
  --disable-gpu \
  --disable-gpu-shader-disk-cache --gpu-disk-cache-size-kb=2048 \
  --no-first-run --no-default-browser-check >> "$LOG" 2>&1 &

for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if alive; then
    echo "$(date '+%F %T') ensure_browser: RECOVERED" >> "$LOG"
    # A hard kill can take the newest cookies with it. Push the vault back in so the loop wakes up
    # already logged in — a re-login means 2FA, and 2FA means a human, which is the one thing the
    # loops must never need.
    python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/session_vault.py" restore >> "$LOG" 2>&1 || true
    python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/cdp_tab_gc.py" >> "$LOG" 2>&1 || true
    echo "RECOVERED"
    exit 0
  fi
done

echo "$(date '+%F %T') ensure_browser: FAILED to recover" >> "$LOG"
echo "FAILED"
exit 1
