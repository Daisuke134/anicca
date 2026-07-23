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

CDP="${CLOAK_CDP_BASE_URL:-http://127.0.0.1:9222}"
CDP_PORT="${CDP_DAILY_DRIVER_PORT:-${CDP##*:}}"
LOG="${CDP_GUARD_LOG:-$HOME/.openclaw/logs/cdp-daily-driver-guard.log}"
GUARD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../earn/gig/scripts/cdp_daily_driver_guard.sh"
export CDP_DAILY_DRIVER_PORT="$CDP_PORT"
export SESSION_VAULT_PORT="${SESSION_VAULT_PORT:-$CDP_PORT}"

alive() { curl -s --max-time 4 "$CDP/json/version" >/dev/null 2>&1; }
wait_for_alive() {
  local waited=0
  while [ "$waited" -lt 45 ]; do
    alive && return 0
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}
post_recovery() {
  python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/session_vault.py" restore >> "$LOG" 2>&1 || true
  if [ -n "${CLOAK_BROWSER_OWNER:-}" ]; then
    python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/cdp_tab_gc.py" --owner "$CLOAK_BROWSER_OWNER" >> "$LOG" 2>&1 || true
  fi
}

if alive; then
  # A loop killed with -9 never releases its context, and an orphaned context keeps its tabs alive
  # forever. Every pass comes through here, so this is the one place a reaper cannot be forgotten.
  python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/cdp_context_lease.py" gc --idle-min 45 >/dev/null 2>&1 || true
  echo "ALIVE"
  exit 0
fi

mkdir -p "$(dirname "$LOG")"
echo "$(date '+%F %T') ensure_browser: :$CDP_PORT dead -> managed recovery" >> "$LOG"
if [ -n "${CLOAK_BROWSER_LAUNCHD_LABEL:-}" ]; then
  case "$CLOAK_BROWSER_LAUNCHD_LABEL" in
    *[!A-Za-z0-9._-]*) echo "FAILED: invalid browser launchd label"; exit 1 ;;
  esac
  if launchctl kickstart -k "gui/$(id -u)/$CLOAK_BROWSER_LAUNCHD_LABEL" \
      >> "$LOG" 2>&1 && wait_for_alive; then
    post_recovery
    echo "$(date '+%F %T') ensure_browser: RECOVERED by launchd owner $CLOAK_BROWSER_LAUNCHD_LABEL" >> "$LOG"
    echo "RECOVERED"
    exit 0
  fi
  echo "$(date '+%F %T') ensure_browser: FAILED launchd-owner recovery" >> "$LOG"
  echo "FAILED"
  exit 1
fi

if [ ! -f "$GUARD" ]; then
  echo "FAILED: persistent browser guard missing"
  exit 1
fi

# Use the same launchd-owned persistent CloakBrowser context as the reality verifier. The previous
# raw nohup launch was a second recovery implementation: it could answer the first probe but had no
# owner supervising the browser lifecycle, so normal passes repeatedly fell back to the crash-prone
# path even though a managed recovery already existed.
source "$GUARD"
if cdp_guard_ensure_healthy 4 45; then
  # A hard kill can take the newest cookies with it. Push the vault back in so the loop wakes up
  # already logged in — a re-login means 2FA, and 2FA means a human, which is the one thing the
  # loops must never need.
  post_recovery
  echo "$(date '+%F %T') ensure_browser: RECOVERED by persistent owner" >> "$LOG"
  echo "RECOVERED"
  exit 0
fi

echo "$(date '+%F %T') ensure_browser: FAILED to recover" >> "$LOG"
echo "FAILED"
exit 1
