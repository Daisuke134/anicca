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
! grep -q 'nohup bash ~/profitable-claude/skills/gig-work/gig_pass.sh' "$CLI" || {
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
