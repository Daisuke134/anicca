#!/usr/bin/env bash
# run-red.sh — runs all VSDD RED-phase oracle tests for profitable-article-writer (Sprint 1) and prints a
# summary. Standard test-runner semantics: exits non-zero if ANY test file fails.
#
# In Phase 2a (RED) EVERY test file below is EXPECTED to FAIL — the scripts under gates/, run.sh and
# identity/ are intentionally-unimplemented stubs (NOT_IMPLEMENTED). That is the correct, required RED
# state; Phase 2b (GREEN) implements the real pipeline until every file here reports PASS.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
total=0; passed=0; failed=0
failed_names=""
for t in "$DIR"/test-*.sh; do
  [ -e "$t" ] || continue
  total=$((total+1))
  name="$(basename "$t")"
  echo "=== $name ==="
  if bash "$t"; then
    passed=$((passed+1))
  else
    failed=$((failed+1))
    failed_names="$failed_names $name"
  fi
  echo
done
echo "==================================================="
echo "RED-PHASE SUMMARY: $total test files, $passed PASS, $failed FAIL"
if [ -n "$failed_names" ]; then
  echo "FAILING:"
  for n in $failed_names; do echo "  - $n"; done
fi
[ $failed -eq 0 ] && exit 0 || exit 1
