#!/usr/bin/env bash
# VSDD oracle — REAL (non-FORCE) gates/v0.sh mechanics (contract-review FIND-001 fix). Every other test in
# this suite reaches gates/v0.sh exclusively via ARTICLE_TEST_FORCE_V0, which bypasses the real mechanical
# checklist entirely (see gates/v0.sh:18-26). This file invokes gates/v0.sh DIRECTLY with
# ARTICLE_TEST_FORCE_V0 unset, so the real exists/non-empty/has-heading/line-count>3 check (gates/v0.sh:
# 28-44) is the thing actually being exercised and asserted on.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- (a) well-formed draft: proper heading + adequate size/line-count -> real check PASSes ----------
T="$(mktemp -d)"
D="$T/draft.md"
cat > "$D" <<'EOF'
# A well-formed draft title

This is a body paragraph with real content.

## A subsection

More real content here to push the line count past the minimum.
EOF
unset ARTICLE_TEST_FORCE_V0
OUT="$(bash "$SKILL/gates/v0.sh" "$D" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "well-formed draft: real (non-FORCE) v0.sh check PASSes, rc=0 (rc=$rc): $OUT"
ok "$(echo "$OUT" | grep -q '^V0_RESULT: PASS$' && echo 1 || echo 0)" "well-formed draft: real check emits V0_RESULT: PASS"

# ---------- (b) malformed draft: no heading, too short -> real check FAILs ----------
T2="$(mktemp -d)"
D2="$T2/draft.md"
printf 'no heading here, just one short line\n' > "$D2"
unset ARTICLE_TEST_FORCE_V0
OUT2="$(bash "$SKILL/gates/v0.sh" "$D2" 2>&1)"; rc2=$?
ok "$([ $rc2 -ne 0 ] && echo 1 || echo 0)" "malformed draft (no heading, too short): real (non-FORCE) v0.sh check FAILs, rc!=0 (rc=$rc2): $OUT2"
ok "$(echo "$OUT2" | grep -q '^V0_RESULT: FAIL' && echo 1 || echo 0)" "malformed draft: real check emits V0_RESULT: FAIL"

# ---------- (c) missing draft artifact -> real check FAILs (fail-closed on the file-existence branch too) ----------
T3="$(mktemp -d)"
unset ARTICLE_TEST_FORCE_V0
OUT3="$(bash "$SKILL/gates/v0.sh" "$T3/does-not-exist.md" 2>&1)"; rc3=$?
ok "$([ $rc3 -ne 0 ] && echo 1 || echo 0)" "missing draft artifact: real v0.sh check FAILs, rc!=0 (rc=$rc3): $OUT3"

[ $fails -eq 0 ] && { echo "PASS — real (non-FORCE) gates/v0.sh mechanics"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
