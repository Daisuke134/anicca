#!/usr/bin/env bash
set -uo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)/scripts/publish_finish.sh"
out=$(bash "$S" 2>&1); rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "agent-id required"; then
  echo "PASS"
else
  echo "FAIL rc=$rc"
  exit 1
fi
