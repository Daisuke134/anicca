#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
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
SELF="${VERIFY_LOOPS_SELF_DIR:-$LIFE_MANAGER_REPO/skills/self}"
STATE_DIR="$HOME/.local/state/life-manager/state"; mkdir -p "$STATE_DIR"
LOG="$HOME/.local/state/life-manager/logs/cadence-deadline-check.log"; mkdir -p "$(dirname "$LOG")"
TODAY_JST="${CADENCE_DEADLINE_TODAY_JST_OVERRIDE:-$(TZ=Asia/Tokyo date +%F)}"
# Test-only override seam (mirrors this codebase's own EARN_LEDGER/FOUNDER_TEST convention) so a
# test can exercise both the before-21:00 no-op path and the escalation path deterministically,
# without waiting for or depending on the real wall clock.
NOW_HOUR_JST="${CADENCE_DEADLINE_NOW_HOUR_JST:-$(TZ=Asia/Tokyo date +%H)}"
# 2026-07-12 (Dais, SSOT §2f fate table): pm-earner retired; clip/affiliate/video/bounty turned OFF until
# P2/deferred-revival — cadence-checking an OFF loop makes self-heal revive it (掟3: retire from watchlists first).
CADENCE_LOOPS="gig founder-loop"

# G1 fix (2026-07-11, docs/loop-engineering/23-anicca-loop-architecture-redesign.md TODO G1 /
# docs/superpowers/evidence/LOOPS-TRUTH-AUDIT.md "escalation→self-fix実行のtriggerが切れてる"):
# standalone healthcheck.sh scripts for loops that don't source healthcheck-lib.sh (clip/video/
# clip-promote/connector-style) write a ".<loop>-core-selfheal-request.json" marker when they give
# up restarting a DEAD loop. Its own note says "read this on your next wake" -- but the loop that
# would read it is exactly the one that's dead, so it never wakes to read it. Confirmed 2026-07-11:
# clip-promote-core wrote such a marker (10:04 UTC) and self-fix ran ZERO times that day. Runs on
# EVERY invocation of this script (unlike the 21:00-JST-only Cadence Contract escalation below)
# since this script is already invoked twice a day for free: once by its own dedicated launchd
# (daily 21:05 JST) and once every 6h as a safety net from verify-loops-audit.sh -- giving the
# marker a real trigger with no new launchd job. self-fix.sh is itself idempotent (skips re-spawn
# while a fixer for that loop is still live, <180min hang ceiling) so calling it again here every
# pass is always safe; a marker still present after a fixer already ran (FAILed, or between runs)
# re-escalates naturally on the next pass -- no separate staleness/cooldown math needed.
scan_selfheal_requests() {
  local f loop reason age_h
  for f in "$STATE_DIR"/.*-core-selfheal-request.json; do
    [ -f "$f" ] || continue
    loop="$(python3 -c "
import json
try:
    print(json.load(open('$f')).get('loop') or '')
except Exception:
    print('')" 2>/dev/null)"
    if [ -z "$loop" ]; then
      loop="$(basename "$f" | sed -E 's/^\.//; s/-core-selfheal-request\.json$//')"
    fi
    [ -n "$loop" ] || { echo "$(date '+%F %T') selfheal-request: $f -- could not determine loop name, skipping" >> "$LOG"; continue; }
    reason="$(python3 -c "
import json
try:
    d = json.load(open('$f'))
    print(d.get('reason') or d.get('heal') or d.get('note') or 'selfheal-request marker present')
except Exception:
    print('selfheal-request marker present (unreadable json)')" 2>/dev/null)"
    age_h=$(( ( $(date +%s) - $(stat -f %m "$f" 2>/dev/null || echo "$(date +%s)") ) / 3600 ))
    echo "$(date '+%F %T') selfheal-request: $f (loop=$loop age=${age_h}h) -> self-fix.sh $loop" >> "$LOG"
    bash "$SELF/self-fix.sh" "$loop" "escalated selfheal-request marker $f (age ${age_h}h, written when a healthcheck gave up restarting this loop): $reason. If you resolve it, delete or rename this marker as part of the fix -- if it is still present next pass, it will be re-escalated." >> "$LOG" 2>&1 || true
  done
}
scan_selfheal_requests

# Defensive: only act at/after 21:00 JST even if invoked early (e.g. a manual run, or
# verify-loops-audit.sh's own earlier-in-the-day pass calling this as a safety net).
if ! [ "$NOW_HOUR_JST" -ge 21 ] 2>/dev/null; then
  echo "$(date '+%F %T') before 21:00 JST (hour=$NOW_HOUR_JST) — no-op" >> "$LOG"
  exit 0
fi

# REQ-LV-102 follow-up (2026-07-12, issues #994/#1000): a per-loop, time-boxed, documented
# exception for a Cadence Contract miss that is a FULLY diagnosed, already-in-progress-fix
# EXTERNAL blocker (e.g. a platform account lock under a multi-day recovery timeline) rather than
# a code bug self-fix can act on again. See cadence-known-gaps.json's own header comment for the
# full rationale. This NEVER touches cadence.py's row-exists truth (MET below is unaffected) —
# it only decides whether to spawn ANOTHER context-less self-fix session for a loop we already
# know is blocked and why. Auto-expires: once TODAY_JST > the recorded 'until', this returns
# False again on its own and normal escalation resumes — a wrong ETA guess can't silently persist.
KNOWN_GAPS="$SELF/cadence-known-gaps.json"
known_gap_active() {
  local loop="$1"
  python3 -c "
import json, datetime
try:
    d = json.load(open('$KNOWN_GAPS'))
except Exception:
    d = {}
entry = d.get('$loop') or {}
until = entry.get('until')
active = False
if until:
    try:
        active = datetime.date.fromisoformat('$TODAY_JST') <= datetime.date.fromisoformat(until)
    except Exception:
        active = False
print('True' if active else 'False')
" 2>/dev/null
}

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
      if [ "$(known_gap_active "$L")" = "True" ]; then
        echo "$(date '+%F %T') $L: known-gap active (cadence-known-gaps.json) — suppressing self-fix spawn, already diagnosed as an external blocker with a tracked ETA" >> "$LOG"
      else
        bash "$SELF/self-fix.sh" "$L" "cadence audit: $L's Cadence Contract was NOT met by 21:00 JST today ($TODAY_JST) — diagnose why today's contracted cadence (see $SELF/cadence-contracts.json) did not happen and fix it. This is a DAILY judgment (not artifact staleness): a real pass days ago does NOT satisfy today's contract." >> "$LOG" 2>&1 || true
      fi
    fi
  fi
done
echo "$(date '+%F %T') cadence-deadline-check done" >> "$LOG"
