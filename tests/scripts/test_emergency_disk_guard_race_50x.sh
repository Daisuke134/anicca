#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
for iteration in $(seq 1 50); do
  if ! bash "$ROOT/tests/scripts/test_emergency_disk_guard_e2e.sh" >"/tmp/emergency-guard-race-$iteration.log" 2>&1; then
    echo "race iteration $iteration failed"
    tail -80 "/tmp/emergency-guard-race-$iteration.log"
    exit 1
  fi
  printf 'race iteration %s PASS\n' "$iteration"
done
echo 'PASS: 50/50 short-lived-child churn runs converged safely'
