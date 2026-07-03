#!/usr/bin/env bash
# gates/v05.sh — V0.5 fixed binary craft checklist gate (REQ-5 a-e). A fresh-context adversary scores the
# draft against a FIXED set of binary criteria; PASS = ALL true, any single FALSE => FAIL:
#   (a) opening hook states a reader pain / curiosity / concrete number
#   (b) a CTA to a paid rail is present
#   (c) the free part ends at a payoff cut (the How is withheld)
#   (d) the draft makes NO claim of having executed/run anything, and contains NO error-log/stack-trace
#       text (this is where REQ-3's semantic "no claim of having run" check lives)
#   (e) readability, mechanical: >= 70% of sentences are <= 60 characters (mobile-scannable) — an
#       objective, computable threshold, not a subjective judgment
#
# INTERFACE (honored once implemented in Phase 2b):
#   arg1:    path to the draft artifact to gate
#   env in:  ARTICLE_TEST_FORCE_V05=PASS|FAIL  (test-injection override; test mode only)
#   stdout:  "V05_RESULT: PASS" | "V05_RESULT: FAIL" plus one "V05_CRIT_<a..e>: true|false" line each
#   exit:    0 on PASS, 1 on FAIL (or on a genuine gate error)
#
# Phase 2a RED stub: intentionally unimplemented.
set -uo pipefail
echo "NOT_IMPLEMENTED: gates/v05.sh (Phase 2b implements the fixed binary craft checklist)" >&2
exit 1
