#!/usr/bin/env bash
# _test-fault-injection/run.sh — DELIBERATELY calls a nonexistent command (mirrors §24#1's real
# "franklin-trading CLI missing from PATH" failure pattern) so we can prove, with REAL evidence, that
# the #7 self-heal wiring (healthcheck-runtime-loop.sh -> self-fix.sh) actually detects+repairs a
# broken skill end-to-end. This directory is NOT a registered skill (no SLOT.md/registry entry) and
# is deleted once the self-fix proof is captured — it never runs as part of any real loop.
set -uo pipefail
# Repaired by the #7 self-heal harness: the line below WAS a deliberate fault
# (`this-command-does-not-exist-anywhere --do-the-thing`, exit 127) that proved the
# healthcheck-runtime-loop.sh -> self-fix.sh wiring detects+repairs a broken skill end-to-end.
# The honest no-op below is the repaired form: it does real, clearly-labeled nothing and exits 0.
echo "_test-fault-injection: self-heal validation fault repaired — no-op OK (exit 0)"
exit 0
