#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
TMP=$(mktemp -d /tmp/emergency-guard-reserve.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
STATE_DIR="$HOME_DIR/.openclaw/state"
mkdir -p "$STATE_DIR"

run_at_free() {
  local free=$1
  set +e
  EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" EMERGENCY_GUARD_TEST_FREE_GB="$free" EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=1 bash "$GUARD"
  RUN_RC=$?
  set -e
}

run_at_free 10
test "$RUN_RC" -eq 3 || { echo "10GiB reserve run returned rc=$RUN_RC"; exit 1; }
test -e "$STATE_DIR/disk-pressure.block"
test -e "$STATE_DIR/disk-pressure.alert"
run_at_free 10
test "$RUN_RC" -eq 3 || { echo "repeated 10GiB reserve run returned rc=$RUN_RC"; exit 1; }
run_at_free 11
test "$RUN_RC" -eq 0 || { echo "11GiB release run returned rc=$RUN_RC"; exit 1; }
test ! -e "$STATE_DIR/disk-pressure.block" || { echo 'backpressure remained at release watermark'; exit 1; }
test ! -e "$STATE_DIR/disk-pressure.alert" || { echo 'alert remained at release watermark'; exit 1; }

echo 'PASS: default reserve holds below 11GiB and releases only at 11GiB'
