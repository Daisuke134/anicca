#!/usr/bin/env bash
# VSDD oracle — PROP-19 (REQ-19, Sprint 2): run.sh's REAL (non-ARTICLE_TEST) generate_draft hook has exactly
# THREE reachable states (see verification-architecture.md's PROP-19 row for the canonical statement):
#   (a) a real draft (ARTICLE_REAL_DRAFT_PATH) is supplied -> the running agent's OWN real research+craft
#       content is used VERBATIM; the ARTICLE_TEST=1 boilerplate template is NEVER used in this state.
#   (b) topic/research are declared but no real draft path has been handed off yet -> a documented WIRING
#       SAFETY-NET falls back to the boilerplate template (never a crash, never an empty file); this is NOT
#       the REQ-4b "insufficient research" SKIP trigger and is never reached by the real daily-executor loop
#       (REQ-19), which always supplies topic/research and the authored draft together in one call.
#   (c) nothing at all is supplied -> fail-closed SKIPPED (Sprint-1 default, REQ-4b), zero regression from
#       before this change.
#
# Sprint-2 contract-review FIND-008 fix: states (a) and (b) below previously asserted only `rc -eq 0`, which
# is near-tautological -- run.sh returns rc=0 for EVERY legitimate outcome INCLUDING ABORTED, so it cannot
# discriminate "the hook wired the right content AND the wake actually reached DRAFT" from "the hook wired
# the right content but the wake silently ABORTED downstream" (e.g. because the real, non-forced V0/V0.5
# gates never passed on the given fixture). Both fixtures below are now deliberately constructed to pass the
# REAL (non-FORCE) gates/v0.sh + gates/v05.sh in a single round (a real ARTICLE_JUDGE_V05_RESPONSE is
# supplied, and each draft's readability genuinely satisfies (e)'s >=70%-short-sentences arithmetic), and
# both states now assert `last_wake_result: DRAFT` in STATE.md explicitly -- not merely rc=0.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

BOILERPLATE_MARKER="burn 10+ hours"
REAL_MARKER="PROP19_REAL_CONTENT_MARKER_20260704"

# ---------- (a) real mode, real topic+research+draft supplied -> generate_draft uses the REAL file verbatim,
# AND the real (non-forced) V0/V0.5 gates genuinely PASS on this fixture in round 1, so the wake reaches a
# real DRAFT result (not merely rc=0, which run.sh also returns on ABORTED). ----------
T="$(mktemp -d)"
FIXTURE="$T/real-article.md"
cat > "$FIXTURE" <<EOF
# 実際にこのエージェントが書いた記事

${REAL_MARKER} このセクションは、実際の研究に基づいて書かれた本文です。

これは短い一文です。これも短い一文です。三つ目の短い一文です。四つ目も短い文です。

続きは有料エリアでご覧いただけます。気になる方はぜひ購入してください。
EOF
RESP="$T/judge-response.txt"
printf 'V05_CRIT_a: true\nV05_CRIT_b: true\nV05_CRIT_c: true\nV05_CRIT_d: true\n' > "$RESP"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_TEST_V0_RESULTS ARTICLE_TEST_V05_RESULTS
OUT="$(ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_JUDGE_V05_RESPONSE="$RESP" ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient ARTICLE_REAL_DRAFT_PATH="$FIXTURE" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "real-mode wake with real draft supplied completes, rc=0 (rc=$rc): $OUT"
draft="$T/draft.md"
ok "$([ -f "$draft" ] && echo 1 || echo 0)" "real-mode wake produced a draft.md artifact"
ok "$(grep -qF "$REAL_MARKER" "$draft" 2>/dev/null && echo 1 || echo 0)" "draft.md contains the REAL agent-authored content verbatim"
ok "$(! grep -qF "$BOILERPLATE_MARKER" "$draft" 2>/dev/null && echo 1 || echo 0)" "draft.md does NOT contain the ARTICLE_TEST boilerplate template text"
ok "$(grep -q 'last_wake_result: DRAFT' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "FIND-008: the wake actually reached last_wake_result: DRAFT (not merely rc=0, which run.sh also returns on ABORTED) -- STATE.md: $(cat "$T/STATE.md" 2>/dev/null)"

# ---------- (b) real mode, no ARTICLE_REAL_DRAFT_PATH set but topic+research ARE set -> falls back to the
# existing boilerplate template (never a crash, never an empty file) — this branch stays available for any
# caller that has a topic but hasn't wired real content yet. The boilerplate's own real (non-forced) V0/V0.5
# gate PASS is proven here too (FIND-008), so this state is shown to reach DRAFT just like state (a), not
# merely rc=0. ----------
T2="$(mktemp -d)"
RESP2="$T2/judge-response.txt"
printf 'V05_CRIT_a: true\nV05_CRIT_b: true\nV05_CRIT_c: true\nV05_CRIT_d: true\n' > "$RESP2"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_REAL_DRAFT_PATH
OUT2="$(ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_JUDGE_V05_RESPONSE="$RESP2" ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "real-mode wake with topic but no real draft path completes, rc=0 (rc=$rc2): $OUT2"
draft2="$T2/draft.md"
ok "$([ -f "$draft2" ] && grep -qF "$BOILERPLATE_MARKER" "$draft2" && echo 1 || echo 0)" "no real draft path supplied: falls back to the boilerplate template (unchanged Sprint-1 shape)"
ok "$(grep -q 'last_wake_result: DRAFT' "$T2/STATE.md" 2>/dev/null && echo 1 || echo 0)" "FIND-008: the safety-net boilerplate ALSO genuinely reaches last_wake_result: DRAFT under the real gates (not ABORTED/SKIPPED) -- STATE.md: $(cat "$T2/STATE.md" 2>/dev/null)"

# ---------- (c) real mode, NOTHING supplied (no ARTICLE_REAL_TOPIC/RESEARCH) -> fail-closed SKIP, zero
# regression from Sprint 1's real-mode default.
T3="$(mktemp -d)"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_REAL_TOPIC ARTICLE_REAL_RESEARCH ARTICLE_REAL_DRAFT_PATH ARTICLE_JUDGE_V05_RESPONSE
OUT3="$(ARTICLE_DIR="$T3" AUTONOMY=off bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "real-mode wake with nothing supplied completes cleanly, rc=0 (rc=$rc3): $OUT3"
ok "$(grep -q 'last_wake_result: SKIPPED' "$T3/STATE.md" 2>/dev/null && echo 1 || echo 0)" "real-mode wake with nothing supplied: still fail-closed SKIPPED (zero regression)"

[ $fails -eq 0 ] && { echo "PASS — PROP-19 real content-gen hook uses real content, fails closed with nothing supplied"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
