#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
TMP=$(mktemp -d /tmp/emergency-guard-orphan.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
LEASE_DIR="$HOME_DIR/.openclaw/state/gig-workers"
mkdir -p "$LEASE_DIR"
dead_pid=999999
touch "$LEASE_DIR/$dead_pid.heartbeat" "$LEASE_DIR/$$.heartbeat" "$LEASE_DIR/not-a-pid.heartbeat"

EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" EMERGENCY_GUARD_TEST_FREE_GB=11 bash "$GUARD"

test ! -e "$LEASE_DIR/$dead_pid.heartbeat" || { echo 'dead PID orphan heartbeat survived'; exit 1; }
test -e "$LEASE_DIR/$$.heartbeat" || { echo 'live PID orphan heartbeat was removed'; exit 1; }
test -e "$LEASE_DIR/not-a-pid.heartbeat" || { echo 'invalid heartbeat was removed'; exit 1; }
grep -q $'\t'"$dead_pid"$'\tcleanup\torphan-heartbeat-dead-pid\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'\t'"$$"$'\tpreserve\torphan-heartbeat-live-pid\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'\tnot-a-pid\tpreserve\torphan-heartbeat-invalid-pid\t' "$HOME_DIR/.openclaw/state/emergency-disk-guard-decisions.tsv"

echo 'PASS: only lease-less dead-PID heartbeat is identity-safely removed'
