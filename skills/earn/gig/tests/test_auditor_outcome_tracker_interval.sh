#!/usr/bin/env bash
# M1 (gig loop spec §FH' blind spot): auditor.sh gates gig_outcome_tracker.sh on its own
# interval marker, exactly like the pre-existing reality-verify block. This runs the REAL
# snippet lifted from auditor.sh (not a re-implementation) against fixtures for: not-due,
# due, restart-intent defer, and post-success marker write.  The tracker outcome
# itself is part of the contract: an infrastructure defer (exit 75) or an
# unexpected failure must leave the marker untouched so the next hourly audit
# retries it.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
AUDITOR="$ROOT/auditor.sh"

# Extract the OUTCOME_TRACKER block verbatim, skipping the dirname-dependent first
# assignment line (the harness supplies OUTCOME_TRACKER itself so bash -c doesn't need a
# real BASH_SOURCE[0]). The block contains an inner one-line `fi` (the marker-read guard)
# before its own closing `fi`, so the range must end at the SECOND `^fi$` after the start,
# not the first.
START_LINE=$(grep -n '^OUTCOME_TRACKER_INTERVAL_SECS=' "$AUDITOR" | head -1 | cut -d: -f1)
END_LINE=$(tail -n "+$START_LINE" "$AUDITOR" | grep -n '^fi$' | sed -n '2p' | cut -d: -f1)
END_LINE=$(( START_LINE + END_LINE - 1 ))
SNIPPET=$(sed -n "${START_LINE},${END_LINE}p" "$AUDITOR")
echo "$SNIPPET" | grep -q 'OUTCOME_TRACKER_MARKER=' || { echo "FAIL: could not extract outcome-tracker snippet from auditor.sh"; exit 1; }
echo "$SNIPPET" | grep -q 'RESTART_AGE' || { echo "FAIL: snippet does not reuse RESTART_AGE from the reality-verify block"; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

run_case() {
  local desc="$1" g="$2" now="$3" restart_age="$4" tracker_exe="$5"
  local out
  out=$(G="$g" REALITY_VERIFY_NOW="$now" OUTCOME_TRACKER_MARKER_NOW="$now" RESTART_AGE="$restart_age" OUTCOME_TRACKER="$tracker_exe" \
    bash -c "$SNIPPET"$'\n''echo "MARKER=$(cat "$G/.outcome-tracker-last-start" 2>/dev/null || echo none)"')
  echo "$out"
}

STUB="$TMP/stub-tracker.sh"
cat > "$STUB" <<'EOF'
#!/usr/bin/env bash
echo "invoked" >> "$STUB_CALL_LOG"
exit "${TRACKER_EXIT:-0}"
EOF
chmod +x "$STUB"

# The wrapper contract is intentionally checked here as well as through the
# fixture runs below: all three infrastructure preconditions in the tracker
# have the explicit temporary-defer status, and the default batch is 40 while
# an environment override remains available.
TRACKER_SH="$ROOT/gig_outcome_tracker.sh"
grep -q 'BATCH_LIMIT="${GIG_OUTCOME_BATCH_LIMIT:-40}"' "$TRACKER_SH" \
  || { echo "FAIL: outcome tracker default batch is not 40 with env override"; exit 1; }
[ "$(grep -c 'exit 75' "$TRACKER_SH")" -ge 3 ] \
  || { echo "FAIL: outcome tracker does not use exit 75 for all temporary defers"; exit 1; }
echo 'PASS: tracker default batch=40 and temporary defer exits are explicit'

# Case 1: no marker at all -> due, not deferred by RESTART_AGE -> invoked, exit 0,
# marker written after successful tracking.
G1="$TMP/case1"; mkdir -p "$G1"
CALL_LOG="$TMP/case1.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=0 run_case "no marker" "$G1" 100000 999999 "$STUB")
[ "$(cat "$CALL_LOG")" = "invoked" ] || { echo "FAIL: case1 expected invocation, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=100000" || { echo "FAIL: case1 expected marker written to 100000, got: $OUT"; exit 1; }
echo "PASS: tracker success -> due, invoked, marker written"

# Case 2: marker recent (interval not elapsed) -> not due -> not invoked.
G2="$TMP/case2"; mkdir -p "$G2"
printf '99000\n' > "$G2/.outcome-tracker-last-start"
CALL_LOG="$TMP/case2.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=0 run_case "recent marker" "$G2" 100000 999999 "$STUB")
[ -s "$CALL_LOG" ] && { echo "FAIL: case2 expected no invocation, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=99000" || { echo "FAIL: case2 expected marker unchanged, got: $OUT"; exit 1; }
echo "PASS: recent marker -> not due, not invoked"

# Case 3: marker old (interval elapsed, default 21600s) -> due -> invoked, exit 0,
# marker advanced atomically.
G3="$TMP/case3"; mkdir -p "$G3"
printf '50000\n' > "$G3/.outcome-tracker-last-start"
CALL_LOG="$TMP/case3.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=0 run_case "elapsed marker" "$G3" 100000 999999 "$STUB")
[ "$(cat "$CALL_LOG")" = "invoked" ] || { echo "FAIL: case3 expected invocation, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=100000" || { echo "FAIL: case3 expected marker advanced, got: $OUT"; exit 1; }
echo "PASS: elapsed marker -> due, invoked, marker advanced"

# Case 4: due, but RESTART_AGE fresh (<60s) -> deferred, NOT invoked, marker NOT written.
G4="$TMP/case4"; mkdir -p "$G4"
CALL_LOG="$TMP/case4.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=0 run_case "fresh restart" "$G4" 100000 5 "$STUB")
[ -s "$CALL_LOG" ] && { echo "FAIL: case4 expected no invocation during restart defer, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=none" || { echo "FAIL: case4 expected marker not written, got: $OUT"; exit 1; }
echo "PASS: due but fresh browser restart -> deferred, not invoked, marker not written"

# Case 5: tracker exit 75 (CDP/browser/session temporary defer) -> invocation is attempted,
# but marker is unchanged for the next hourly retry.
G5="$TMP/case5"; mkdir -p "$G5"
printf '70000\n' > "$G5/.outcome-tracker-last-start"
CALL_LOG="$TMP/case5.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=75 run_case "tracker defer" "$G5" 100000 999999 "$STUB")
[ "$(cat "$CALL_LOG")" = "invoked" ] || { echo "FAIL: case5 expected tracker invocation, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=70000" || { echo "FAIL: case5 expected marker unchanged after exit75, got: $OUT"; exit 1; }
echo "PASS: tracker exit75 -> marker unchanged for next retry"

# Case 6: tracker exits unexpectedly -> marker is also unchanged, while the
# isolated auditor snippet continues and does not convert failure into success.
G6="$TMP/case6"; mkdir -p "$G6"
printf '71000\n' > "$G6/.outcome-tracker-last-start"
CALL_LOG="$TMP/case6.calls"; : > "$CALL_LOG"
OUT=$(STUB_CALL_LOG="$CALL_LOG" TRACKER_EXIT=42 run_case "tracker failure" "$G6" 100000 999999 "$STUB")
[ "$(cat "$CALL_LOG")" = "invoked" ] || { echo "FAIL: case6 expected tracker invocation, log=$(cat "$CALL_LOG")"; exit 1; }
echo "$OUT" | grep -q "MARKER=71000" || { echo "FAIL: case6 expected marker unchanged after failure, got: $OUT"; exit 1; }
echo "PASS: tracker failure -> marker unchanged and auditor continues"

# Case 7: non-executable tracker path -> never invoked, never crashes (missing script must
# never abort the audit run).
NOEXEC="$TMP/does-not-exist.sh"
G7="$TMP/case7"; mkdir -p "$G7"
OUT=$(run_case "missing script" "$G7" 100000 999999 "$NOEXEC")
echo "$OUT" | grep -q "MARKER=none" || { echo "FAIL: case7 expected marker not written for a missing script, got: $OUT"; exit 1; }
echo "PASS: missing/non-executable tracker script -> silently skipped, no crash"

echo 'PASS: auditor.sh outcome-tracker interval gate matches the reality-verify block pattern'
