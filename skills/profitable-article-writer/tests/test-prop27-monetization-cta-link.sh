#!/usr/bin/env bash
# VSDD oracle -- PROP-27 (REQ-27, Sprint 5): the "view -> yen" funnel's monetization-link half. Every wake
# that reaches a BOTH-PASS gate result (Mode A DRAFT or Mode B PUBLISHED/UNCONFIRMED) appends a deterministic
# monetization link to the gated draft -- via insert_monetization_link() in run.sh, called AFTER the V0/V0.5
# gate loop succeeds so it never perturbs the agent's own craft-judged CTA prose or V05_CRIT_b's scoring of
# it -- unless the caller explicitly opts out with ARTICLE_CTA_URL="" (the literal empty string, distinct
# from leaving it unset).
#
# Dynamic SKILL resolution (not the sibling tests' hardcoded main-tree path): this file must test WHATEVER
# tree it physically lives in (a feature worktree during development, the main tree after merge).
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- happy path: default CTA appended (Mode A DRAFT) ----------
T1="$(mktemp -d)"
OUT1="$(ARTICLE_TEST=1 ARTICLE_DIR="$T1" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc1=$?
ok "$([ $rc1 -eq 0 ] && echo 1 || echo 0)" "wake completes, rc=0 (rc=$rc1): $OUT1"
draft1="$(grep -oE '^draft_path: .*' "$T1/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -n "$draft1" ] && [ -f "$draft1" ] && echo 1 || echo 0)" "draft artifact produced"
ok "$([ -f "$draft1" ] && grep -q 'https://aniccaai.com/' "$draft1" && echo 1 || echo 0)" "default monetization link (DEFAULT_CTA_URL) appended to the gated draft body"
ok "$(grep -q '^cta_url: https://aniccaai.com/' "$T1/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md records the cta_url actually appended"

# ---------- happy path: custom CTA_URL/CTA_TEXT override used verbatim ----------
T2="$(mktemp -d)"
OUT2="$(ARTICLE_TEST=1 ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  ARTICLE_CTA_URL="https://example.com/custom-product" ARTICLE_CTA_TEXT="今すぐ見る" \
  bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "wake completes with override, rc=0 (rc=$rc2): $OUT2"
draft2="$(grep -oE '^draft_path: .*' "$T2/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -f "$draft2" ] && grep -q 'https://example.com/custom-product' "$draft2" && echo 1 || echo 0)" "custom ARTICLE_CTA_URL is used verbatim, not the default"
ok "$([ -f "$draft2" ] && grep -q '今すぐ見る' "$draft2" && echo 1 || echo 0)" "custom ARTICLE_CTA_TEXT is used verbatim"
ok "$(grep -q '^cta_url: https://example.com/custom-product' "$T2/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md records the custom cta_url"

# ---------- failure/opt-out path: ARTICLE_CTA_URL="" (explicit empty) -> NO link appended, never crashes ----------
T3="$(mktemp -d)"
OUT3="$(ARTICLE_TEST=1 ARTICLE_DIR="$T3" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" ARTICLE_CTA_URL="" \
  bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "wake completes with explicit opt-out, rc=0 (rc=$rc3): $OUT3"
draft3="$(grep -oE '^draft_path: .*' "$T3/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -f "$draft3" ] && ! grep -q 'https://aniccaai.com/' "$draft3" && echo 1 || echo 0)" "explicit ARTICLE_CTA_URL=\"\" -> no monetization link appended (opt-out honored, not a crash)"
ok "$(grep -q '^cta_url: $' "$T3/STATE.md" 2>/dev/null && echo 1 || echo 0)" "STATE.md's cta_url is empty when opted out (distinguishable from a real link)"

# ---------- ABORTED wakes never get a CTA link appended (gates never passed -> no publish -> no funnel) ----------
T4="$(mktemp -d)"
OUT4="$(ARTICLE_TEST=1 ARTICLE_DIR="$T4" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="FAIL,FAIL,FAIL" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc4=$?
ok "$([ $rc4 -eq 0 ] && echo 1 || echo 0)" "ABORTED wake still exits 0 (rc=$rc4): $OUT4"
ok "$(grep -q 'last_wake_result: ABORTED' "$T4/STATE.md" 2>/dev/null && echo 1 || echo 0)" "wake correctly ABORTED (3-round ceiling, no BOTH-PASS)"
ok "$(! grep -q '^cta_url:' "$T4/STATE.md" 2>/dev/null && echo 1 || echo 0)" "ABORTED wake's STATE.md has no cta_url field at all (link is never inserted before a gate PASS)"

[ $fails -eq 0 ] && { echo "PASS -- PROP-27 monetization link: default appended + STATE-recorded, override honored verbatim, explicit opt-out never crashes, never inserted before gates PASS"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
