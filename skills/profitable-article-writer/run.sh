#!/usr/bin/env bash
# run.sh — profitable-article-writer 1-wake entrypoint (REQ-4, REQ-4b, REQ-6, REQ-7, REQ-9, REQ-12, REQ-14).
#
# INTERFACE (honored once implemented in Phase 2b), mirroring skills/self/founder-loop's env-injectable
# test-mode convention so the wake is deterministically testable with no real agent judgment or network
# call:
#   env in:  ARTICLE_DIR               state dir (STATE.md, state/accounts.json, state/failures.jsonl,
#                                       state/PUBLISHED all live here)
#   env in:  AUTONOMY                  "on" = Mode B (autonomous publish, REQ-7); anything else
#                                       (default "off") = Mode A (draft + notify, REQ-6)
#   env in:  ARTICLE_TEST=1            deterministic test mode — no real research/craft/gate calls; the
#                                       values below are injected instead
#   env in:  ARTICLE_TEST_TOPIC        injected topic string; EMPTY => no viable topic (REQ-4b SKIP)
#   env in:  ARTICLE_TEST_RESEARCH     "sufficient" | "insufficient" (REQ-4b SKIP if insufficient)
#   env in:  ARTICLE_TEST_V0_RESULTS   comma list, one PASS|FAIL per fix+re-gate round (REQ-14, max 3)
#   env in:  ARTICLE_TEST_V05_RESULTS  comma list, one PASS|FAIL per fix+re-gate round (REQ-14, max 3)
#   env in:  ARTICLE_TEST_MODE         named deterministic scenario for isolated sub-path checks, e.g.
#                                       "record_earn_only" => exercises ONLY the record-earn call and
#                                       prints "RECORD_EARN_NO_LLM: true" (REQ-12, PROP-9)
#   writes:  $ARTICLE_DIR/STATE.md     last_wake_result: SKIPPED|DRAFT|PUBLISHED|ABORTED, rounds_used,
#                                      draft_path, publish_url (Mode B only), notify_path (Mode A only)
#   exit:    0 for every LEGITIMATE outcome — SKIPPED/DRAFT/PUBLISHED/ABORTED are all valid, non-error
#            wake results (REQ-4b and REQ-14 are expected control flow, not failures); non-zero only on a
#            genuine harness error.
#
# Phase 2a RED stub: intentionally unimplemented.
set -uo pipefail
echo "NOT_IMPLEMENTED: run.sh (Phase 2b implements the 1-wake pipeline: pick topic -> research -> decide ->" >&2
echo "  write -> de-slop -> V0/V0.5 gate loop, <=3 rounds -> Mode A draft+notify OR Mode B publish+distribute)" >&2
exit 1
