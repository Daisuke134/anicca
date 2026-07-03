#!/usr/bin/env bash
# gates/v0.sh — V0 render/slop gate (REQ-5; reuses the existing note-publish vision-check pattern).
#
# INTERFACE (honored once implemented in Phase 2b):
#   arg1:    path to the draft artifact to gate
#   env in:  ARTICLE_TEST_FORCE_V0=PASS|FAIL   (test-injection override; test mode only)
#   stdout:  "V0_RESULT: PASS" | "V0_RESULT: FAIL"
#   exit:    0 on PASS, 1 on FAIL (or on a genuine gate error)
#
# Phase 2a RED stub: intentionally unimplemented.
set -uo pipefail
echo "NOT_IMPLEMENTED: gates/v0.sh (Phase 2b implements the render/slop gate)" >&2
exit 1
