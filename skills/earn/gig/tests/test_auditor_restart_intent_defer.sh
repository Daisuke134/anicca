#!/usr/bin/env bash
# gig_pass.sh's B2 wedge-retry drops a restart-intent file before kickstart -k'ing the
# shared browser (spec Sec-ES'). auditor.sh reads it before its hourly reality-verify
# CDP call and defers if the restart was <60s ago. This runs the REAL snippet lifted
# from auditor.sh (not a re-implementation) against three fixtures.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
AUDITOR="$ROOT/auditor.sh"
PY=/opt/homebrew/bin/python3
[ -x "$PY" ] || PY=$(command -v python3)

# Extract the RESTART_* block verbatim so the test tracks the real code, not a copy.
SNIPPET=$(sed -n '/^RESTART_INTENT_FILE=/,/^fi$/p' "$AUDITOR" | head -9)
echo "$SNIPPET" | grep -q 'RESTART_AGE=999999' || { echo "FAIL: could not extract restart-intent snippet from auditor.sh"; exit 1; }

run_case() {
  local desc="$1" home="$2" now="$3" expect_defer="$4"
  local out
  out=$(HOME="$home" PY="$PY" REALITY_VERIFY_NOW="$now" bash -c "$SNIPPET"$'\n''echo "RESTART_AGE=$RESTART_AGE"')
  local age
  age=$(echo "$out" | sed -n 's/^RESTART_AGE=//p')
  if [ "$expect_defer" = yes ]; then
    if [ "$age" -ge 0 ] && [ "$age" -lt 60 ]; then echo "PASS: $desc (age=$age)"; else echo "FAIL: $desc expected defer, age=$age"; exit 1; fi
  else
    if [ "$age" -ge 60 ]; then echo "PASS: $desc (age=$age)"; else echo "FAIL: $desc expected no-defer, age=$age"; exit 1; fi
  fi
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Case 1: no intent file at all -> never defers.
NOFILE="$TMP/nofile"; mkdir -p "$NOFILE/.openclaw/state"
run_case "no intent file" "$NOFILE" "$(date +%s)" no

# Case 2: fresh intent (5s old) -> defers.
FRESH="$TMP/fresh"; mkdir -p "$FRESH/.openclaw/state"
NOW=$(date +%s)
printf '{"ts":%s,"by":"gig-pass-B2-wedge-retry","reason":"cdp_browser_wedged"}\n' "$((NOW - 5))" > "$FRESH/.openclaw/state/gig-browser-restart-intent.json"
run_case "fresh intent (5s)" "$FRESH" "$NOW" yes

# Case 3: stale intent (1h old) -> does not defer.
STALE="$TMP/stale"; mkdir -p "$STALE/.openclaw/state"
printf '{"ts":%s,"by":"gig-pass-B2-wedge-retry","reason":"cdp_browser_wedged"}\n' "$((NOW - 3600))" > "$STALE/.openclaw/state/gig-browser-restart-intent.json"
run_case "stale intent (1h)" "$STALE" "$NOW" no

echo 'PASS: auditor.sh restart-intent snippet defers only within the 60s window'
