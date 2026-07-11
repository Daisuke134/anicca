#!/usr/bin/env bash
# test-healthcheck-lib.sh — FIND-014: prove the stuck-asking detector fires ONLY on idle input-await prompts and
# NEVER on active generation ("esc to interrupt") or healthy idle. Mirrors the exact predicate in healthcheck-lib.sh.
set -uo pipefail; P=0; F=0
# FIND-021: source the REAL predicate from the lib (no duplication → cannot drift).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)/healthcheck-lib.sh"
chk(){ local name="$1" want="$2" pane="$3"; if hc_is_stuck_pane "$pane"; then got=FIRE; else got=OK; fi
  [ "$got" = "$want" ] && { echo "  ok $name ($got)"; P=$((P+1)); } || { echo "  FAIL $name want=$want got=$got"; F=$((F+1)); }; }

# idle interactive picker (asking a human) → FIRE (restart)
chk "idle picker menu" FIRE '  1. Option A
  2. Option B
Enter to select · ↑/↓ to navigate · Esc to cancel
❯'
# active generation that happens to show a menu-ish word BUT esc-to-interrupt present → must NOT fire
chk "active generation (esc to interrupt)" OK '✻ Brewed for 3m · esc to interrupt
Enter to select something later'
# healthy idle after a pass (just prompt) → NOT fire
chk "healthy idle prompt" OK '⏺ done. touched last-pass.
❯'
# free-text await → FIRE
chk "free-text await" FIRE 'Type something. or use @ to mention
❯'
# confirm dialog → FIRE
chk "confirm dialog" FIRE 'Do you want to proceed?
  1. Yes
  2. No'
# active searching, no prompt → NOT fire
chk "active searching" OK '✢ Searching… (7m · ↓ 19k tokens · esc to interrupt)'

# FIND-034: hc_recent_restart must gate the STALE-restart path so a restart storm can't pre-empt a
# pass before it finishes (the pass touches the heartbeat only at its own final step).
chkr(){ local name="$1" want="$2" log="$3" now="$4"; if hc_recent_restart "$log" "$now"; then got=FIRE; else got=OK; fi
  [ "$got" = "$want" ] && { echo "  ok $name ($got)"; P=$((P+1)); } || { echo "  FAIL $name want=$want got=$got"; F=$((F+1)); }; }

TMPLOG="$(mktemp)"
printf '' > "$TMPLOG"
chkr "no restart log at all" OK "/tmp/.does-not-exist-$$" 1000000
printf '999000\n' > "$TMPLOG"
chkr "restart 1000s ago (within 1200s grace)" FIRE "$TMPLOG" 1000000
printf '997000\n' > "$TMPLOG"
chkr "restart 3000s ago (past 1200s grace)" OK "$TMPLOG" 1000000
rm -f "$TMPLOG"

# G2 item4: hc_last_pass_recent -- a genuinely-completed-pass marker touched within max_age_min
# means the loop is healthy right now, regardless of session-liveness alone (real connector
# incident 2026-07-11: session-liveness-only judgment DEAD-misjudged a healthy once-daily-cron loop).
chkp(){ local name="$1" want="$2"; shift 2; if hc_last_pass_recent "$@"; then got=TRUE; else got=FALSE; fi
  [ "$got" = "$want" ] && { echo "  ok $name ($got)"; P=$((P+1)); } || { echo "  FAIL $name want=$want got=$got"; F=$((F+1)); }; }

HBFILE="$(mktemp)"
touch "$HBFILE"   # mtime = now
chkp "just-touched marker, max_age=60min" TRUE "$HBFILE" 60
# back-date the marker to 90min ago (older than the 60min window)
OLD_TS=$(( $(date +%s) - 90*60 ))
touch -t "$(date -r "$OLD_TS" +%Y%m%d%H%M.%S 2>/dev/null || date -j -f %s "$OLD_TS" +%Y%m%d%H%M.%S)" "$HBFILE" 2>/dev/null || \
  python3 -c "import os,sys; t=float(sys.argv[1]); os.utime(sys.argv[2], (t,t))" "$OLD_TS" "$HBFILE"
chkp "marker 90min old, max_age=60min -> FALSE (stale)" FALSE "$HBFILE" 60
chkp "marker 90min old, max_age=120min -> TRUE (still within window)" TRUE "$HBFILE" 120
rm -f "$HBFILE"
chkp "marker file missing entirely -> FALSE" FALSE "/tmp/.does-not-exist-hc-last-pass-$$" 60

echo "=== healthcheck-lib stall-detect: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
