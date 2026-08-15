#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
LAUNCHER="$SKILL_DIR/scripts/launch_gig_worker.sh"
CLI="$SKILL_DIR/gig-cli.sh"
TMP=$(mktemp -d /tmp/gig-worker-launcher.XXXXXX)
export GIG_WORK_EVENT_PROJECTOR=/usr/bin/true
export GIG_WORK_EVENT_PROJECTOR_LOG="$TMP/work-event-projector.log"
export GIG_WORKER_REPORTS_ENABLED=0
launcher_pid=""
worker_pid=""
cleanup() {
  [ -n "$worker_pid" ] && /bin/kill -KILL "-$worker_pid" 2>/dev/null || true
  [ -n "$launcher_pid" ] && kill -TERM "$launcher_pid" 2>/dev/null || true
  [ -n "$launcher_pid" ] && wait "$launcher_pid" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT

test -x "$LAUNCHER" || { echo 'missing executable launch_gig_worker.sh'; exit 1; }
! grep -q 'nohup bash $GIG_DIR/gig_pass.sh' "$CLI" || {
  echo 'gig-cli still launches gig_pass.sh directly without a lease'
  exit 1
}
! grep -Eiq 'claude[[:space:]]+-p|codex[[:space:]]+exec|--model[=[:space:]]+sonnet' "$CLI" || {
  echo 'gig core supervisor directly invokes a provider'
  exit 1
}
grep -q 'GIG_WORKER_LEASE_ACTIVE' "$SKILL_DIR/gig_pass.sh" || {
  echo 'legacy direct gig_pass entry does not converge on the lease launcher'
  exit 1
}

cat > "$TMP/preflight-worker.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
touch "$GIG_FIXTURE_STARTED_FILE"
sleep 0.2
EOF
chmod +x "$TMP/preflight-worker.sh"
STOP_FLAG="$TMP/state/disk-writers.stop"
mkdir -p "${STOP_FLAG%/*}"

touch "$STOP_FLAG"
set +e
GIG_WORKER_SCRIPT="$TMP/preflight-worker.sh" \
GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
GIG_WORKER_TEST_FREE_GB=20 \
GIG_FIXTURE_STARTED_FILE="$TMP/started-by-stop-flag" \
bash "$LAUNCHER" >"$TMP/stop-flag.out" 2>"$TMP/stop-flag.err"
stop_flag_rc=$?
set -e
test "$stop_flag_rc" -eq 78
test ! -e "$TMP/started-by-stop-flag"
grep -q 'disk preflight blocked: stop flag present' "$TMP/stop-flag.err"

rm -f "$STOP_FLAG"
set +e
GIG_WORKER_SCRIPT="$TMP/preflight-worker.sh" \
GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
GIG_WORKER_TEST_FREE_GB=4 \
GIG_WORKER_MIN_FREE_GB=5 \
GIG_FIXTURE_STARTED_FILE="$TMP/started-by-low-space" \
bash "$LAUNCHER" >"$TMP/low-space.out" 2>"$TMP/low-space.err"
low_space_rc=$?
set -e
test "$low_space_rc" -eq 78
test ! -e "$TMP/started-by-low-space"
grep -q 'disk preflight blocked: free_gb=4 minimum_gb=5' "$TMP/low-space.err"

touch "$TMP/state/disk-pressure.block"
GIG_WORKER_SCRIPT="$TMP/preflight-worker.sh" \
GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
GIG_WORKER_TEST_FREE_GB=10 \
GIG_WORKER_MIN_FREE_GB=5 \
GIG_FIXTURE_STARTED_FILE="$TMP/started-by-pressure-advisory" \
bash "$LAUNCHER" >"$TMP/pressure-advisory.out" 2>"$TMP/pressure-advisory.err"
test -e "$TMP/started-by-pressure-advisory"
grep -q 'disk pressure advisory present; continuing with free_gb=10 minimum_gb=5' "$TMP/pressure-advisory.err"
rm -f "$TMP/state/disk-pressure.block"

# ─── silent death is as loud as silent success (A1) ────────────────────────────
# A blocked pass used to leave nothing but one line per hour in a launchd log; the
# loop was dead ten hours on 2026-07-30 and Dais had no way to know. Fault-inject
# the same block and assert ONE outage event, no per-hour repeat, ONE recovery.
# Everything is redirected into $TMP: no live outbox row, no real Telegram send.
PY=/opt/homebrew/bin/python3
OUTAGE_GIG="$TMP/gig"
OUTAGE_DB="$OUTAGE_GIG/telegram-outbox.sqlite3"
mkdir -p "$OUTAGE_GIG" "$TMP/bin"
cat > "$TMP/bin/openclaw" <<'EOF'
#!/usr/bin/env bash
# Stand-in for the Telegram transport: proves the message reached the sender
# without putting anything on Dais's real chat.
printf '%s\n' "$*" >> "$OPENCLAW_STUB_LOG"
printf '{"messageId":"stub-%s"}\n' "$RANDOM"
EOF
chmod +x "$TMP/bin/openclaw"
export OPENCLAW_STUB_LOG="$TMP/openclaw-stub.log"
: > "$OPENCLAW_STUB_LOG"

outage_rows() {
  "$PY" - "$OUTAGE_DB" "$1" <<'EOF'
import sqlite3, sys
from pathlib import Path
database, kind = Path(sys.argv[1]), sys.argv[2]
if not database.exists():
    print(0)
    raise SystemExit(0)
connection = sqlite3.connect(database)
print(connection.execute(
    "SELECT COUNT(*) FROM telegram_reports WHERE kind=?", (kind,)
).fetchone()[0])
EOF
}

run_gate() {
  set +e
  GIG_WORKER_SCRIPT="$TMP/preflight-worker.sh" \
  GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
  GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
  GIG_WORKER_LEASE_DIR="$TMP/state/gig-workers" \
  GIG_WORKER_TEST_FREE_GB="$1" \
  GIG_WORKER_MIN_FREE_GB=5 \
  GIG_WORKER_REPORTS_ENABLED=0 \
  GIG_WORKER_PASS_OUTAGE_REPORTS_ENABLED=1 \
  GIG_WORKER_GIG_DIR="$OUTAGE_GIG" \
  GIG_WORKER_OPENCLAW="$TMP/bin/openclaw" \
  GIG_FIXTURE_STARTED_FILE="$TMP/started-by-gate-$2" \
  bash "$LAUNCHER" >"$TMP/gate-$2.out" 2>"$TMP/gate-$2.err"
  gate_rc=$?
  set -e
}

touch "$STOP_FLAG"
run_gate 20 blocked-first
test "$gate_rc" -eq 78
test "$(outage_rows pass_outage)" -eq 1 || {
  echo "a blocked pass must record exactly one outage event, got $(outage_rows pass_outage)"
  exit 1
}
test "$(outage_rows pass_recovered)" -eq 0

# The same stop flag an hour later: still blocked, still exactly one event.
run_gate 20 blocked-second
test "$gate_rc" -eq 78
test "$(outage_rows pass_outage)" -eq 1 || {
  echo "an unchanged outage re-alerted; that is the ten-per-outage spam this exists to prevent"
  exit 1
}

rm -f "$STOP_FLAG"
run_gate 20 recovered
test "$gate_rc" -eq 0
test -e "$TMP/started-by-gate-recovered"
test "$(outage_rows pass_recovered)" -eq 1 || {
  echo "a recovered pass must announce recovery exactly once"
  exit 1
}
run_gate 20 recovered-second
test "$(outage_rows pass_recovered)" -eq 1

# The reader is Dais, not an operator: no exit codes, no lane names, no pass IDs.
"$PY" - "$OUTAGE_DB" <<'EOF'
import sqlite3, sys
from pathlib import Path
connection = sqlite3.connect(Path(sys.argv[1]))
rows = connection.execute(
    "SELECT kind,message,state FROM telegram_reports ORDER BY report_id"
).fetchall()
assert rows, "no report rows were produced at all"
for kind, message, state in rows:
    assert state == "sent", f"{kind} never reached the transport: {state}"
    for jargon in ("78", "exit", "lane", "pass_id", "preflight", "rc="):
        assert jargon not in message, f"{jargon!r} leaked into {kind}: {message}"
    print(f"--- {kind} ({state}) ---\n{message}")
EOF
grep -q 'message send' "$OPENCLAW_STUB_LOG" || {
  echo 'outage events never reached the Telegram transport'
  exit 1
}

# The launcher must stay silent when the existing kill switch is off, or every
# unrelated test run would post to Dais's real chat.
rm -f "$OUTAGE_DB"
touch "$STOP_FLAG"
set +e
GIG_WORKER_SCRIPT="$TMP/preflight-worker.sh" \
GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
GIG_WORKER_TEST_FREE_GB=20 \
GIG_WORKER_REPORTS_ENABLED=0 \
GIG_WORKER_GIG_DIR="$OUTAGE_GIG" \
bash "$LAUNCHER" >/dev/null 2>&1
set -e
test ! -e "$OUTAGE_DB" || { echo 'outage reporting ignored the reports kill switch'; exit 1; }
rm -f "$STOP_FLAG"

cat > "$TMP/worker.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sleep 300 &
printf '%s\n' "$!" > "$GIG_FIXTURE_CHILD_FILE"
while :; do sleep 1; done
EOF
chmod +x "$TMP/worker.sh"
LEASE_DIR="$TMP/state/gig-workers"
READY="$TMP/ready"
mkdir -p "$LEASE_DIR"

GIG_WORKER_SCRIPT="$TMP/worker.sh" \
GIG_WORKER_LEASE_DIR="$LEASE_DIR" \
GIG_WORKER_HEARTBEAT_INTERVAL=1 \
GIG_WORKER_READY_FILE="$READY" \
GIG_WORKER_DISK_STOP_FLAG="$STOP_FLAG" \
GIG_WORKER_DISK_PRESSURE_FLAG="$TMP/state/disk-pressure.block" \
GIG_WORKER_TEST_FREE_GB=20 \
GIG_FIXTURE_CHILD_FILE="$TMP/child" \
bash "$LAUNCHER" >"$TMP/launcher.log" 2>&1 &
launcher_pid=$!
for _ in $(seq 1 100); do [ -s "$READY" ] && [ -s "$TMP/child" ] && break; sleep 0.1; done
test -s "$READY"
worker_pid=$(cat "$READY")
child_pid=$(cat "$TMP/child")
LEASE="$LEASE_DIR/$worker_pid.lease"
HEARTBEAT="$LEASE_DIR/$worker_pid.heartbeat"
test -f "$LEASE"
test -f "$HEARTBEAT"
for partial in "$LEASE".*.tmp; do
  test ! -e "$partial" || { echo "partial lease became visible: $partial"; exit 1; }
done

expected_start=$(ps -p "$worker_pid" -o lstart= | awk '{$1=$1; print}')
expected_pgid=$(ps -p "$worker_pid" -o pgid= | awk '{$1=$1; print}')
expected_argv=$(ps -p "$worker_pid" -o command= | awk '{$1=$1; print}')
worker_snapshot=$(printf '%s\n' "$expected_argv" | sed -n 's#^/bin/bash \(.*\/gig_pass\.sh\.[^/[:space:]]*\)$#\1#p')
test "$worker_pid" = "$expected_pgid"
test -n "$worker_snapshot" || {
  echo "worker is executing the mutable source script: $expected_argv"
  exit 1
}
test -f "$worker_snapshot"
cmp -s "$TMP/worker.sh" "$worker_snapshot" || {
  echo 'worker snapshot did not preserve the launch-time script bytes'
  exit 1
}
grep -qx "pid=$worker_pid" "$LEASE"
grep -qx "start_token=$expected_start" "$LEASE"
grep -qx "pgid=$expected_pgid" "$LEASE"
grep -qx "canonical_argv=$expected_argv" "$LEASE"

first_mtime=$(stat -f %m "$HEARTBEAT")
sleep 2
second_mtime=$(stat -f %m "$HEARTBEAT")
test "$second_mtime" -gt "$first_mtime" || { echo 'heartbeat did not advance'; exit 1; }

/bin/kill -TERM "-$worker_pid"
wait "$launcher_pid" || true
launcher_pid=""
if kill -0 "$worker_pid" 2>/dev/null; then echo 'worker survived group stop'; exit 1; fi
if kill -0 "$child_pid" 2>/dev/null; then echo 'child survived group stop'; exit 1; fi
test ! -e "$LEASE"
test ! -e "$HEARTBEAT"
test ! -e "$worker_snapshot"

echo 'PASS: launcher snapshots code, atomically leases a dedicated PGID, beats, and cleans up'
