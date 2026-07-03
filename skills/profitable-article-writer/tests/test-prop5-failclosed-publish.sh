#!/usr/bin/env bash
# VSDD oracle — PROP-5 (REQ-5, REQ-14): fail-closed publish wiring. A FAIL from V0 OR V0.5 MUST mean
# publish is NEVER called; only a BOTH-PASS round reaches publish.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
mk(){ local d; d="$(mktemp -d)"; mkdir -p "$d/state"; printf 'draft body\n' > "$d/draft.md"; echo "$d"; }

# 1. V0 FAIL, V0.5 PASS -> no publish
T="$(mk)"
OUT="$(ARTICLE_DIR="$T" ARTICLE_TEST_FORCE_V0=FAIL ARTICLE_TEST_FORCE_V05=PASS bash "$SKILL/gates/publish-gate.sh" "$T/draft.md" 2>&1)"; rc=$?
ok "$([ ! -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "V0=FAIL,V05=PASS: publish sentinel absent (fail-closed)"
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "V0=FAIL,V05=PASS: gate returns non-zero (rc=$rc)"

# 2. V0 PASS, V0.5 FAIL -> no publish
T="$(mk)"
OUT="$(ARTICLE_DIR="$T" ARTICLE_TEST_FORCE_V0=PASS ARTICLE_TEST_FORCE_V05=FAIL bash "$SKILL/gates/publish-gate.sh" "$T/draft.md" 2>&1)"; rc=$?
ok "$([ ! -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "V0=PASS,V05=FAIL: publish sentinel absent (fail-closed)"
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "V0=PASS,V05=FAIL: gate returns non-zero (rc=$rc)"

# 3. V0 FAIL, V0.5 FAIL -> no publish
T="$(mk)"
OUT="$(ARTICLE_DIR="$T" ARTICLE_TEST_FORCE_V0=FAIL ARTICLE_TEST_FORCE_V05=FAIL bash "$SKILL/gates/publish-gate.sh" "$T/draft.md" 2>&1)"; rc=$?
ok "$([ ! -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "V0=FAIL,V05=FAIL: publish sentinel absent (fail-closed)"

# 4. V0 PASS, V0.5 PASS -> publish sentinel exists, rc=0 (the ONLY path that publishes)
T="$(mk)"
OUT="$(ARTICLE_DIR="$T" ARTICLE_TEST_FORCE_V0=PASS ARTICLE_TEST_FORCE_V05=PASS bash "$SKILL/gates/publish-gate.sh" "$T/draft.md" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "V0=PASS,V05=PASS: publish sentinel written, rc=0 (rc=$rc — $OUT)"

[ $fails -eq 0 ] && { echo "PASS — PROP-5 fail-closed publish wiring (only both-PASS reaches publish)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
