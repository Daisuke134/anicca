#!/usr/bin/env bash
# gates/publish-gate.sh — fail-closed publish wiring (REQ-5, REQ-7, REQ-14; PROP-5).
#
# Contract: publish is called IF AND ONLY IF gates/v0.sh AND gates/v05.sh BOTH return PASS. A FAIL from
# EITHER gate means publish is NEVER called (fail-closed). Up to 3 fix+re-gate rounds are allowed
# (REQ-14); after 3 consecutive FAILs the wake ABORTS with no publish and a failure entry is recorded.
#
# INTERFACE (honored once implemented in Phase 2b):
#   arg1:    path to the draft artifact
#   env in:  ARTICLE_DIR (state dir)
#   env in:  ARTICLE_TEST_FORCE_V0 / ARTICLE_TEST_FORCE_V05 (test-injection: PASS|FAIL, single round here;
#            multi-round ceiling behavior is exercised via run.sh's ARTICLE_TEST_V0_RESULTS/V05_RESULTS)
#   writes:  $ARTICLE_DIR/state/PUBLISHED       sentinel — created ONLY on a successful publish call
#   writes:  $ARTICLE_DIR/state/failures.jsonl  append-only failure record on 3-round abort (REQ-14)
#   exit:    0 = published; 1 = aborted (no publish); NEVER a partial state (fail-closed)
#
# Phase 2a RED stub: intentionally unimplemented.
set -uo pipefail
echo "NOT_IMPLEMENTED: gates/publish-gate.sh (Phase 2b implements fail-closed publish wiring)" >&2
exit 1
