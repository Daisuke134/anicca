#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
LAUNCHER="/Users/anicca/profitable-claude/skills/gig-work/scripts/launch_gig_worker.sh"
FIXTURE="$ROOT/tests/scripts/fixtures/gig_pass_fixture.sh"
TMP=$(mktemp -d /tmp/emergency-guard-e2e.XXXXXX)
LAUNCHERS=""
TRACKED_PGIDS=""
cleanup() {
  for pgid in $TRACKED_PGIDS; do /bin/kill -KILL "-$pgid" 2>/dev/null || true; done
  for launcher in $LAUNCHERS; do kill -TERM "$launcher" 2>/dev/null || true; done
  for launcher in $LAUNCHERS; do wait "$launcher" 2>/dev/null || true; done
  rm -rf "$TMP"
}
trap cleanup EXIT

test -x "$LAUNCHER" || { echo "production launcher missing: $LAUNCHER"; exit 1; }
HOME_DIR="$TMP/home"
LEASE_DIR="$HOME_DIR/.openclaw/state/gig-workers"
mkdir -p "$LEASE_DIR"
CANONICAL_ARGV="/bin/bash $FIXTURE"

wait_for_file() {
  local file=$1
  for _ in $(seq 1 100); do [ -s "$file" ] && return 0; sleep 0.1; done
  return 1
}

launch_managed() {
  local name=$1 heartbeat_interval=$2 churn=${3:-0} child_file ready_file
  child_file="$TMP/$name-child"
  ready_file="$TMP/$name-ready"
  GIG_WORKER_SCRIPT="$FIXTURE" \
  GIG_WORKER_LEASE_DIR="$LEASE_DIR" \
  GIG_WORKER_HEARTBEAT_INTERVAL="$heartbeat_interval" \
  GIG_WORKER_READY_FILE="$ready_file" \
  GIG_FIXTURE_CHILD_FILE="$child_file" \
  GIG_FIXTURE_CHURN="$churn" \
  bash "$LAUNCHER" >"$TMP/$name-launcher.log" 2>&1 &
  MANAGED_LAUNCHER=$!
  LAUNCHERS="$LAUNCHERS $MANAGED_LAUNCHER"
  wait_for_file "$ready_file"
  wait_for_file "$child_file"
  MANAGED_PID=$(cat "$ready_file")
  MANAGED_CHILD=$(cat "$child_file")
  TRACKED_PGIDS="$TRACKED_PGIDS $MANAGED_PID"
}

launch_managed stale 300 1
stale_launcher=$MANAGED_LAUNCHER
stale_pid=$MANAGED_PID
stale_child=$MANAGED_CHILD
sleep 1.2
touch -t 202001010000 "$LEASE_DIR/$stale_pid.heartbeat"
launch_managed healthy 1
healthy_pid=$MANAGED_PID
healthy_child=$MANAGED_CHILD

# A same-argv, dedicated-PGID worker without a lease must remain fail-closed.
GIG_FIXTURE_CHILD_FILE="$TMP/no-lease-child" python3 -c \
  'import os,sys; os.setpgid(0,0); os.execv("/bin/bash", ["/bin/bash", sys.argv[1]])' "$FIXTURE" &
no_lease_pid=$!
TRACKED_PGIDS="$TRACKED_PGIDS $no_lease_pid"
wait_for_file "$TMP/no-lease-child"

test "$stale_pid" = "$(ps -p "$stale_pid" -o pgid= | awk '{$1=$1; print}')"
test "$healthy_pid" = "$(ps -p "$healthy_pid" -o pgid= | awk '{$1=$1; print}')"
test -f "$LEASE_DIR/$stale_pid.lease"
test -f "$LEASE_DIR/$healthy_pid.lease"

set +e
EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" \
EMERGENCY_GUARD_TEST_FREE_GB=2 \
EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=0 \
GIG_WORKER_MAX_SECONDS=0 \
GIG_HEARTBEAT_MAX_SECONDS=3 \
GIG_WORKER_CANONICAL_ARGV="$CANONICAL_ARGV" \
bash "$GUARD"
guard_rc=$?
set -e
test "$guard_rc" -ne 0 || { echo 'zero-reclaim cross-repo emergency returned success'; exit 1; }

! kill -0 "$stale_pid" 2>/dev/null || { echo 'stale managed parent survived'; exit 1; }
! kill -0 "$stale_child" 2>/dev/null || { echo 'stale managed child survived'; exit 1; }
wait "$stale_launcher" 2>/dev/null || true
kill -0 "$healthy_pid" 2>/dev/null || { echo 'healthy managed worker was stopped'; exit 1; }
kill -0 "$healthy_child" 2>/dev/null || { echo 'healthy managed child was stopped'; exit 1; }
kill -0 "$no_lease_pid" 2>/dev/null || { echo 'no-lease worker was not preserved fail-closed'; exit 1; }
test ! -e "$LEASE_DIR/$stale_pid.lease" || { echo 'stale lease was not cleaned after worker exit'; exit 1; }
test ! -e "$LEASE_DIR/$stale_pid.heartbeat" || { echo 'stale heartbeat was not cleaned after worker exit'; exit 1; }
test -e "$LEASE_DIR/$healthy_pid.lease"
grep -q $'^.*\t'"$stale_pid"$'\tstopped\tstale-runaway\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'^.*\t'"$healthy_pid"$'\tpreserve\tfresh-heartbeat\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"
if grep -q $'^.*\t'"$no_lease_pid"$'\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"; then
  echo 'no-lease worker was evaluated'
  exit 1
fi

echo 'PASS: production launcher contract stops stale tree, preserves healthy and no-lease workers'
