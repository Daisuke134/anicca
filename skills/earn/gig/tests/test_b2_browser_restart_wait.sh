#!/usr/bin/env bash
# The B2 wedged-browser retry used to fire a fixed `sleep 12` after the launchd
# kick, but the fresh browser's DevTools port opens ~14-15s later (measured
# twice: 06:12:36->06:12:50, 08:12:57->08:13:12) -- the retry ran against a
# browser that was not listening yet, so self-heal succeeded 1/7 times. This
# pins the fix as source text: the dead CDP_FORCE_RESTART call is gone, the
# kickstart is still there, and a port-readiness poll with settle sleep
# replaced the fixed sleep.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
FILE="$SKILL_DIR/gig_pass.sh"

# 1. The dead no-op call is gone. CDP_FORCE_RESTART was never read by
#    ensure_browser.sh (grep-verified), so the call did nothing but mask the
#    real recovery path below it.
grep -q 'CDP_FORCE_RESTART' "$FILE" \
  && { echo 'FAIL: dead CDP_FORCE_RESTART call is still present'; exit 1; }

# 2. The launchd kick that actually restarts the gig browser is preserved.
grep -q 'launchctl kickstart -k "gui/\$(id -u)/\${CLOAK_BROWSER_LAUNCHD_LABEL:-ai.anicca.hf-gig-browser}"' "$FILE" \
  || { echo 'FAIL: the launchd kickstart was removed'; exit 1; }

# 3. The fixed `sleep 12` is gone, replaced by a readiness poll against the
#    gig browser's own CDP port.
grep -q '^      sleep 12$' "$FILE" \
  && { echo 'FAIL: fixed sleep 12 is still present instead of a readiness poll'; exit 1; }
grep -q 'GIG_BROWSER_PORT:-9223}/json/version' "$FILE" \
  || { echo 'FAIL: no readiness poll against the gig browser CDP port'; exit 1; }

# 4. The poll budget mirrors ensure_browser.sh's own 45s wait_for_alive, not
#    an arbitrarily different number.
grep -q 'b2_restart_waited.*-lt 45' "$FILE" \
  || { echo 'FAIL: readiness poll is not bounded to 45s'; exit 1; }

# 5. A short settle sleep still runs after readiness, so a retry does not race
#    session/cookie restore the instant the port opens.
grep -A5 'GIG_BROWSER_PORT:-9223}/json/version' "$FILE" | grep -Eq '^[[:space:]]+done$' \
  || { echo 'FAIL: poll loop is not closed before the retry'; exit 1; }
grep -A8 'b2_restart_waited=0' "$FILE" | tail -1 | grep -Eq '^[[:space:]]+sleep [0-9]+$' \
  || { echo 'FAIL: no settle sleep after readiness poll'; exit 1; }

echo 'PASS: B2 wedged-browser retry polls for readiness instead of a fixed sleep, kickstart intact'
