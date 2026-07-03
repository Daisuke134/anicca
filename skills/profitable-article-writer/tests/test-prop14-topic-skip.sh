#!/usr/bin/env bash
# VSDD oracle — PROP-14 (REQ-4b): no-viable-topic OR insufficient-research -> the wake SKIPS (produces no
# article) rather than emitting a thin/slop piece.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# 1. no viable topic (empty)
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" ARTICLE_TEST_TOPIC="" ARTICLE_TEST_RESEARCH=sufficient bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "no-viable-topic wake completes cleanly, rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'last_wake_result: SKIPPED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "no-viable-topic -> STATE result SKIPPED"
ok "$(! grep -q '^draft_path: ' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "no-viable-topic -> NO article/draft produced"

# 2. insufficient research
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=insufficient bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "insufficient-research wake completes cleanly, rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'last_wake_result: SKIPPED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "insufficient-research -> STATE result SKIPPED"
ok "$(! grep -q '^draft_path: ' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "insufficient-research -> NO article/draft produced"

[ $fails -eq 0 ] && { echo "PASS — PROP-14 no-viable-topic/insufficient-research -> SKIP, never slop"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
