#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
FIXTURE="$ROOT/tests/scripts/fixtures/gig_pass_fixture.sh"
TMP=$(mktemp -d /tmp/emergency-guard-e2e.XXXXXX)
PIDS=""
cleanup() {
  for pid in $PIDS; do /bin/kill -KILL "-$pid" 2>/dev/null || true; done
  for pid in $PIDS; do wait "$pid" 2>/dev/null || true; done
  rm -rf "$TMP"
}
trap cleanup EXIT

HOME_DIR="$TMP/home"
LEASE_DIR="$HOME_DIR/.openclaw/state/gig-workers"
mkdir -p "$LEASE_DIR"
CANONICAL_ARGV="/bin/bash $FIXTURE"

spawn_group() {
  local child_file=$1
  GIG_FIXTURE_CHILD_FILE="$child_file" python3 -c 'import os,sys; os.setpgid(0,0); os.execv("/bin/bash", ["/bin/bash", sys.argv[1]])' "$FIXTURE" &
  SPAWNED_PID=$!
  PIDS="$PIDS $SPAWNED_PID"
  for _ in $(seq 1 50); do [ -s "$child_file" ] && break; sleep 0.1; done
  test -s "$child_file"
}

process_start() { ps -p "$1" -o lstart= | awk '{$1=$1; print}'; }
process_pgid() { ps -p "$1" -o pgid= | awk '{$1=$1; print}'; }

spawn_group "$TMP/stale-child"
stale_pid=$SPAWNED_PID
stale_child=$(cat "$TMP/stale-child")
stale_start=$(process_start "$stale_pid")
stale_pgid=$(process_pgid "$stale_pid")
test "$stale_pid" = "$stale_pgid"
cat > "$LEASE_DIR/$stale_pid.lease" <<EOF
pid=$stale_pid
start_token=$stale_start
pgid=$stale_pgid
canonical_argv=$CANONICAL_ARGV
EOF

spawn_group "$TMP/healthy-child"
healthy_pid=$SPAWNED_PID
healthy_start=$(process_start "$healthy_pid")
healthy_pgid=$(process_pgid "$healthy_pid")
test "$healthy_pid" = "$healthy_pgid"
cat > "$LEASE_DIR/$healthy_pid.lease" <<EOF
pid=$healthy_pid
start_token=$healthy_start
pgid=$healthy_pgid
canonical_argv=$CANONICAL_ARGV
EOF
touch "$LEASE_DIR/$healthy_pid.heartbeat"

sleep 2
EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" \
EMERGENCY_GUARD_TEST_FREE_GB=2 \
EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=0 \
GIG_WORKER_MAX_SECONDS=1 \
GIG_HEARTBEAT_MAX_SECONDS=180 \
GIG_WORKER_CANONICAL_ARGV="$CANONICAL_ARGV" \
bash "$GUARD"

! kill -0 "$stale_pid" 2>/dev/null || { echo 'stale parent survived'; exit 1; }
! kill -0 "$stale_child" 2>/dev/null || { echo 'stale child survived'; exit 1; }
wait "$stale_pid" 2>/dev/null || true
kill -0 "$healthy_pid" 2>/dev/null || { echo 'healthy worker was stopped'; exit 1; }
grep -q $'^.*\t'"$stale_pid"$'\tstopped\tstale-runaway\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'^.*\t'"$healthy_pid"$'\tpreserve\tfresh-heartbeat\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"

echo 'PASS: real dedicated group stopped with child; healthy leased group preserved'
