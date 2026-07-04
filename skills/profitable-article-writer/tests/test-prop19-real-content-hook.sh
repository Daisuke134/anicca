#!/usr/bin/env bash
# VSDD oracle — PROP-19 (REQ-19, Sprint 2): run.sh's REAL (non-ARTICLE_TEST) generate_draft hook uses the
# running agent's OWN real research+craft content (supplied via ARTICLE_REAL_DRAFT_PATH) VERBATIM, never the
# ARTICLE_TEST=1 boilerplate template — and stays fail-closed to SKIPPED (Sprint-1 default, REQ-4b) when no
# real topic/research has been supplied, exactly as before this change (zero regression).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

BOILERPLATE_MARKER="burn 10+ hours"
REAL_MARKER="PROP19_REAL_CONTENT_MARKER_20260704"

# ---------- (a) real mode, real topic+research+draft supplied -> generate_draft uses the REAL file verbatim ----------
T="$(mktemp -d)"
FIXTURE="$T/real-article.md"
cat > "$FIXTURE" <<EOF
# 実際にこのエージェントが書いた記事

${REAL_MARKER} このセクションは、実際の研究に基づいて書かれた本文です。
EOF
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_TEST_V0_RESULTS ARTICLE_TEST_V05_RESULTS
OUT="$(ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient ARTICLE_REAL_DRAFT_PATH="$FIXTURE" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "real-mode wake with real draft supplied completes, rc=0 (rc=$rc): $OUT"
draft="$T/draft.md"
ok "$([ -f "$draft" ] && echo 1 || echo 0)" "real-mode wake produced a draft.md artifact"
ok "$(grep -qF "$REAL_MARKER" "$draft" 2>/dev/null && echo 1 || echo 0)" "draft.md contains the REAL agent-authored content verbatim"
ok "$(! grep -qF "$BOILERPLATE_MARKER" "$draft" 2>/dev/null && echo 1 || echo 0)" "draft.md does NOT contain the ARTICLE_TEST boilerplate template text"

# ---------- (b) real mode, no ARTICLE_REAL_DRAFT_PATH set but topic+research ARE set -> falls back to the
# existing boilerplate template (never a crash, never an empty file) — this branch stays available for any
# caller that has a topic but hasn't wired real content yet.
T2="$(mktemp -d)"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_REAL_DRAFT_PATH
OUT2="$(ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "real-mode wake with topic but no real draft path completes, rc=0 (rc=$rc2): $OUT2"
draft2="$T2/draft.md"
ok "$([ -f "$draft2" ] && grep -qF "$BOILERPLATE_MARKER" "$draft2" && echo 1 || echo 0)" "no real draft path supplied: falls back to the boilerplate template (unchanged Sprint-1 shape)"

# ---------- (c) real mode, NOTHING supplied (no ARTICLE_REAL_TOPIC/RESEARCH) -> fail-closed SKIP, zero
# regression from Sprint 1's real-mode default.
T3="$(mktemp -d)"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_REAL_TOPIC ARTICLE_REAL_RESEARCH ARTICLE_REAL_DRAFT_PATH
OUT3="$(ARTICLE_DIR="$T3" AUTONOMY=off bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "real-mode wake with nothing supplied completes cleanly, rc=0 (rc=$rc3): $OUT3"
ok "$(grep -q 'last_wake_result: SKIPPED' "$T3/STATE.md" 2>/dev/null && echo 1 || echo 0)" "real-mode wake with nothing supplied: still fail-closed SKIPPED (zero regression)"

[ $fails -eq 0 ] && { echo "PASS — PROP-19 real content-gen hook uses real content, fails closed with nothing supplied"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
