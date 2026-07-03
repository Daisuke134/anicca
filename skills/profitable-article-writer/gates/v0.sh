#!/usr/bin/env bash
# gates/v0.sh — V0 render/slop gate (REQ-5; reuses the existing note-publish vision-check pattern).
#
# INTERFACE:
#   arg1:    path to the draft artifact to gate
#   env in:  ARTICLE_TEST_FORCE_V0=PASS|FAIL   (test-injection override; test mode only)
#   stdout:  "V0_RESULT: PASS" | "V0_RESULT: FAIL"
#   exit:    0 on PASS, 1 on FAIL (or on a genuine gate error)
#
# Phase 2b GREEN: when ARTICLE_TEST_FORCE_V0 is set, honor it verbatim (deterministic test seam — the real
# browser/screenshot vision check is reused from the existing note-publish pattern and wired live in
# Sprint 2). Otherwise this gate does the part of V0 that IS mechanically checkable without a browser: the
# draft artifact must exist, be non-empty, have a heading, and have more than just the heading (a body).
set -uo pipefail

DRAFT="${1:-}"

if [ -n "${ARTICLE_TEST_FORCE_V0:-}" ]; then
  if [ "$ARTICLE_TEST_FORCE_V0" = "PASS" ]; then
    echo "V0_RESULT: PASS"
    exit 0
  else
    echo "V0_RESULT: FAIL"
    exit 1
  fi
fi

if [ -z "$DRAFT" ] || [ ! -f "$DRAFT" ]; then
  echo "V0_RESULT: FAIL (no draft artifact at '$DRAFT')"
  exit 1
fi

size="$(wc -c < "$DRAFT" 2>/dev/null | tr -d ' ')"
has_heading=0
grep -qE '^#[[:space:]]' "$DRAFT" 2>/dev/null && has_heading=1
line_count="$(wc -l < "$DRAFT" 2>/dev/null | tr -d ' ')"

if [ "${size:-0}" -gt 0 ] && [ "$has_heading" = 1 ] && [ "${line_count:-0}" -gt 3 ]; then
  echo "V0_RESULT: PASS"
  exit 0
fi

echo "V0_RESULT: FAIL (empty draft, missing heading, or too thin — size=$size heading=$has_heading lines=$line_count)"
exit 1
