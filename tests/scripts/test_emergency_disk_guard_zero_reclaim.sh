#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
TMP=$(mktemp -d /tmp/emergency-guard-zero.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
STATE_DIR="$HOME_DIR/.openclaw/state"
mkdir -p "$STATE_DIR"
LIVE_LEGACY="${EMERGENCY_GUARD_LIVE_LEGACY_LEDGER:-/Users/anicca/.openclaw/state/emergency-disk-guard-reclaim.tsv}"
LEGACY_COPY="$STATE_DIR/emergency-disk-guard-reclaim.tsv"
if [ -f "$LIVE_LEGACY" ]; then
  cp "$LIVE_LEGACY" "$LEGACY_COPY"
else
  printf 'legacy\tpath\towner\tclass\t0\treason\tpolicy\tfailed\n' > "$LEGACY_COPY"
fi
legacy_hash=$(shasum -a 256 "$LEGACY_COPY" | awk '{print $1}')
legacy_lines=$(wc -l < "$LEGACY_COPY" | tr -d ' ')

run_guard() {
  set +e
  EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" \
  EMERGENCY_GUARD_TEST_FREE_GB=2 \
  EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=1 \
  bash "$GUARD"
  local rc=$?
  set -e
  printf '%s\n' "$rc"
}

rc1=$(run_guard)
rc2=$(run_guard)
test "$rc1" -ne 0 || { echo 'first zero-reclaim emergency returned success'; exit 1; }
test "$rc2" -ne 0 || { echo 'second zero-reclaim emergency returned success'; exit 1; }
test -e "$STATE_DIR/disk-pressure.block" || { echo 'backpressure was cleared'; exit 1; }
test -e "$STATE_DIR/disk-pressure.alert" || { echo 'zero-reclaim alert missing'; exit 1; }
test "$(shasum -a 256 "$LEGACY_COPY" | awk '{print $1}')" = "$legacy_hash" || { echo 'copied live v1 ledger changed'; exit 1; }
test "$(wc -l < "$LEGACY_COPY" | tr -d ' ')" = "$legacy_lines"
awk -F '\t' 'NF != 12 { exit 1 }' "$STATE_DIR/emergency-disk-guard-reclaim-v2.tsv"
grep -q $'\tdisk-pressure\tfailure\tno-eligible-reclaim\t' "$STATE_DIR/emergency-disk-guard-decisions.tsv"
test "$(grep -c $'\tfailure\tno-eligible-reclaim\t' "$STATE_DIR/emergency-disk-guard-ops-v2.tsv")" -eq 2
test "$(head -1 "$STATE_DIR/emergency-disk-guard-ops-v2.tsv")" = $'timestamp\tresult\treason\tfree_before_gb\tfree_after_gb\teligible_paths\treclaimed_bytes\tpolicy_version'
awk -F '\t' 'NF != 8 { exit 1 }' "$STATE_DIR/emergency-disk-guard-ops-v2.tsv"

echo 'PASS: repeated zero-reclaim emergency is nonzero, alerted, and backpressured'
