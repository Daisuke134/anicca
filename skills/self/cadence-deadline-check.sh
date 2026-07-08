#!/usr/bin/env bash
# cadence-deadline-check.sh — REQ-LV-102 (F-ITER3-1 fix): the "21:00 JST — did today's Cadence
# Contract get met" escalation, extracted into its OWN script so it can be triggered by a
# StartCalendarInterval (Hour=21, Minute=5, JST) launchd job — guaranteed to fire once a day at a
# fixed wall-clock time. The old approach relied on verify-loops-audit.sh's rolling
# StartInterval(6h) happening to land inside the [21:00,24:00) window, which depends on an unstable
# launchd-load-time offset: for roughly half of all possible offsets, that window is NEVER hit on
# any given day, so REQ-LV-102's escalation condition would go permanently unevaluated (the exact
# bug iteration-3 adversary review caught). This script is also still called from
# verify-loops-audit.sh's own 6h pass as a redundant safety net — harmless, since the per-loop
# marker file below makes a second call on the same JST day a no-op (whichever caller runs first
# claims the marker).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
SELF="${VERIFY_LOOPS_SELF_DIR:-$HOME/anicca/skills/self}"
STATE_DIR="$HOME/.openclaw/state"; mkdir -p "$STATE_DIR"
LOG="$HOME/.openclaw/logs/cadence-deadline-check.log"; mkdir -p "$(dirname "$LOG")"
TODAY_JST="$(TZ=Asia/Tokyo date +%F)"
# Test-only override seam (mirrors this codebase's own EARN_LEDGER/FOUNDER_TEST convention) so a
# test can exercise both the before-21:00 no-op path and the escalation path deterministically,
# without waiting for or depending on the real wall clock.
NOW_HOUR_JST="${CADENCE_DEADLINE_NOW_HOUR_JST:-$(TZ=Asia/Tokyo date +%H)}"
CADENCE_LOOPS="clip affiliate video gig bounty pm-earner founder-loop"

# Defensive: only act at/after 21:00 JST even if invoked early (e.g. a manual run, or
# verify-loops-audit.sh's own earlier-in-the-day pass calling this as a safety net).
if ! [ "$NOW_HOUR_JST" -ge 21 ] 2>/dev/null; then
  echo "$(date '+%F %T') before 21:00 JST (hour=$NOW_HOUR_JST) — no-op" >> "$LOG"
  exit 0
fi

for L in $CADENCE_LOOPS; do
  STATUS_JSON="$(python3 "$SELF/cadence-evidence.py" status "$L" 2>>"$LOG")"
  MET="$(printf '%s' "$STATUS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['met'])" 2>/dev/null || echo False)"
  # REQ-LV-102: escalate at most once per loop per JST calendar day (marker file) — never
  # suppressed by a past-days success (the exact bug class REQ-LV-101's row-exists/increment/
  # recency dispatch fixes).
  if [ "$MET" = "False" ]; then
    MK="$STATE_DIR/.cadence-escalated-$L-$TODAY_JST"
    if [ ! -f "$MK" ]; then
      touch "$MK"
      bash "$SELF/self-fix.sh" "$L" "cadence audit: $L's Cadence Contract was NOT met by 21:00 JST today ($TODAY_JST) — diagnose why today's contracted cadence (see $SELF/cadence-contracts.json) did not happen and fix it. This is a DAILY judgment (not artifact staleness): a real pass days ago does NOT satisfy today's contract." >> "$LOG" 2>&1 || true
    fi
  fi
done
echo "$(date '+%F %T') cadence-deadline-check done" >> "$LOG"
