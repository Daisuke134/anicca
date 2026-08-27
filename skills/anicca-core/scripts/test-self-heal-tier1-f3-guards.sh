#!/usr/bin/env bash
# test-self-heal-tier1-f3-guards.sh — F3 must not kill healthy services.
#
# Real incident 2026-07-27 10:19 JST: gig_pass.sh logged
#   ".../gig_pass.sh: line 1270: record_lane_attempt: command not found"
# (an UNDEFINED SHELL FUNCTION — defined 100 lines below its first call, already fixed
# in gig-work). tier1-remediate.sh classified it as F3_binary_missing, ran
# `brew install record_lane_attempt` (failed, obviously), then `launchctl kickstart -k`
# anyway — SIGTERMing a healthy in-flight worker whose detached codex child then held
# the gig browser lock as an orphan for 12 minutes (next pass: deferred_cdp_busy, 75).
# Ledger evidence: ~/.openclaw/state/self-heal-ledger.jsonl 2026-07-27T01:19:19Z.
#
# Two guards under test, both via real throwaway launchd jobs (no mocks, HARD RULE 0.24;
# never touches production services; cooldown cleared for throwaway keys only):
#   GUARD 1 — a name that is a shell function DEFINED IN THE ERRORING SCRIPT ITSELF is
#             not a missing binary: no brew, no kickstart, no F3 ledger entry.
#   GUARD 2 — when install fails and the binary is still missing, DO NOT kickstart:
#             restarting without the binary cannot fix anything and only kills work.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
LEDGER="$ANICCA_HOME/state/self-heal-ledger.jsonl"
TIER1="$ANICCA_HOME/skills/anicca-core/scripts/tier1-remediate.sh"

PASS=0; FAIL=0
check() {
  if [ "$1" -eq 0 ]; then echo "PASS: $2"; PASS=$((PASS+1));
  else echo "FAIL: $2"; FAIL=$((FAIL+1)); fi
}
job_pid() { launchctl list "$1" 2>/dev/null | grep '"PID"' | tr -cd '0-9'; }

FNFP_LABEL="ai.anicca.tier1-f3-fnfp-test"
NOKICK_LABEL="ai.anicca.tier1-f3-nokick-test"
FNFP_PLIST="$HOME/Library/LaunchAgents/$FNFP_LABEL.plist"
NOKICK_PLIST="$HOME/Library/LaunchAgents/$NOKICK_LABEL.plist"
TESTDIR=$(mktemp -d /tmp/tier1-f3-guards.XXXXXX)
cleanup() {
  launchctl unload "$FNFP_PLIST" >/dev/null 2>&1 || true
  launchctl unload "$NOKICK_PLIST" >/dev/null 2>&1 || true
  rm -f "$FNFP_PLIST" "$NOKICK_PLIST"
  rm -rf "$TESTDIR"
}
trap cleanup EXIT

make_job() { # $1=label $2=plist $3=errlog
  cat > "$2" <<PLISTXML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$1</string>
  <key>ProgramArguments</key>
  <array><string>/bin/sh</string><string>-c</string><string>sleep 3600</string></array>
  <key>WorkingDirectory</key><string>$TESTDIR</string>
  <key>StandardErrorPath</key><string>$3</string>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
PLISTXML
  launchctl load "$2" >/dev/null 2>&1
  sleep 1
}

echo "=== GUARD 1: shell function undefined in its own script is NOT a missing binary ==="
# A real script that DOES define the "missing" name — exactly the gig_pass.sh shape.
cat > "$TESTDIR/fnfp-job.sh" <<'EOF'
#!/usr/bin/env bash
main() { my_internal_helper_fn "x"; }
my_internal_helper_fn() { echo "defined lower in the file"; }
main "$@"
EOF
cat > "$TESTDIR/fnfp.err.log" <<EOF
some prior harmless log line
$TESTDIR/fnfp-job.sh: line 2: my_internal_helper_fn: command not found
EOF
make_job "$FNFP_LABEL" "$FNFP_PLIST" "$TESTDIR/fnfp.err.log"
PID_BEFORE=$(job_pid "$FNFP_LABEL")
[ -n "$PID_BEFORE" ]
check $? "fnfp throwaway job is genuinely running (precondition, pid=$PID_BEFORE)"
rm -f "$ANICCA_HOME/state/remediation-cooldown/F3_${FNFP_LABEL}_my_internal_helper_fn.last"
LINES_BEFORE=$(grep -c "$FNFP_LABEL" "$LEDGER" 2>/dev/null); LINES_BEFORE=${LINES_BEFORE:-0}

bash "$TIER1" >/tmp/tier1-f3-guards-run1.out 2>&1

LINES_AFTER=$(grep -c "$FNFP_LABEL" "$LEDGER" 2>/dev/null); LINES_AFTER=${LINES_AFTER:-0}
[ "$LINES_AFTER" -eq "$LINES_BEFORE" ]
check $? "no F3 ledger entry for a shell-function false positive"
PID_AFTER=$(job_pid "$FNFP_LABEL")
[ -n "$PID_AFTER" ] && [ "$PID_AFTER" = "$PID_BEFORE" ]
check $? "service NOT kickstarted for a shell-function false positive (pid $PID_BEFORE -> ${PID_AFTER:-gone})"
! brew list my_internal_helper_fn >/dev/null 2>&1
check $? "no brew formula was installed for the function name"

echo
echo "=== GUARD 2: failed install must leave the running service alone ==="
cat > "$TESTDIR/nokick.err.log" <<'EOF'
some prior harmless log line
sh: zz-no-such-formula-xq: command not found
EOF
make_job "$NOKICK_LABEL" "$NOKICK_PLIST" "$TESTDIR/nokick.err.log"
PID_BEFORE=$(job_pid "$NOKICK_LABEL")
[ -n "$PID_BEFORE" ]
check $? "nokick throwaway job is genuinely running (precondition, pid=$PID_BEFORE)"
rm -f "$ANICCA_HOME/state/remediation-cooldown/F3_${NOKICK_LABEL}_zz-no-such-formula-xq.last"

bash "$TIER1" >/tmp/tier1-f3-guards-run2.out 2>&1

THROWAWAY_LINE=$(grep "$NOKICK_LABEL" "$LEDGER" | tail -1)
printf '%s' "$THROWAWAY_LINE" | grep -q '"verify_result": "still_missing"'
check $? "ledger still records the still_missing escalation (observability kept)"
PID_AFTER=$(job_pid "$NOKICK_LABEL")
[ -n "$PID_AFTER" ] && [ "$PID_AFTER" = "$PID_BEFORE" ]
check $? "service NOT kickstarted when install failed (pid $PID_BEFORE -> ${PID_AFTER:-gone})"

echo
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
