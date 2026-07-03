#!/usr/bin/env bash
# VSDD oracle — REAL (non-FORCE) gates/v05.sh mechanics (contract-review FIND-001 fix). Every other test in
# this suite reaches gates/v05.sh exclusively via ARTICLE_TEST_FORCE_V05, which bypasses both the real
# criterion-(e) readability arithmetic AND the real judge_v05 response-file parser entirely (see
# gates/v05.sh:46-56). This file invokes gates/v05.sh DIRECTLY with ARTICLE_TEST_FORCE_V05 unset, so:
#   (a) criterion (e)'s REAL sentence-length arithmetic (gates/v05.sh:104-122), and
#   (b) the REAL judge_v05 response-file parser for (a)-(d) (gates/v05.sh:88-100), including its
#       fail-closed-when-unwired default,
# are the things actually being exercised and asserted on.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- (a) criterion (e): real sentence-length arithmetic ----------

# short-sentence draft -> >=70% of sentences <=60 chars -> real arithmetic computes crit_e=true
T="$(mktemp -d)"
D="$T/draft.md"
cat > "$D" <<'EOF'
# Short sentence draft

This is short. Also short here. Another short one. Yet another short one.
EOF
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT="$(bash "$SKILL/gates/v05.sh" "$D" 2>&1)"
ok "$(echo "$OUT" | grep -q '^V05_CRIT_e: true$' && echo 1 || echo 0)" "short-sentence draft: real (e) sentence-length arithmetic computes crit_e=true (>=70% <=60 chars): $OUT"

# long-sentence draft -> more than 30% of sentences exceed 60 chars -> real arithmetic computes crit_e=false
T2="$(mktemp -d)"
D2="$T2/draft.md"
cat > "$D2" <<'EOF'
# Long sentence draft

This sentence is intentionally written to be extremely long so that it exceeds sixty characters easily. Here is another deliberately long sentence crafted specifically to exceed the sixty character threshold for this test. Short one here.
EOF
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT2="$(bash "$SKILL/gates/v05.sh" "$D2" 2>&1)"
ok "$(echo "$OUT2" | grep -q '^V05_CRIT_e: false$' && echo 1 || echo 0)" "long-sentence draft (2/3 sentences >60 chars): real (e) arithmetic computes crit_e=false (<70% <=60 chars): $OUT2"

# ---------- (b) judge_v05 response-file parser: (a)-(d) parsed from a REAL response file ----------

T3="$(mktemp -d)"
D3="$T3/draft.md"
cp "$D" "$D3"
RESP="$T3/response.txt"
cat > "$RESP" <<'EOF'
V05_CRIT_a: true
V05_CRIT_b: true
V05_CRIT_c: true
V05_CRIT_d: true
EOF
unset ARTICLE_TEST_FORCE_V05
OUT3="$(ARTICLE_JUDGE_V05_RESPONSE="$RESP" bash "$SKILL/gates/v05.sh" "$D3" 2>&1)"; rc3=$?
ok "$(echo "$OUT3" | grep -q '^V05_CRIT_a: true$' && echo "$OUT3" | grep -q '^V05_CRIT_b: true$' && echo "$OUT3" | grep -q '^V05_CRIT_c: true$' && echo "$OUT3" | grep -q '^V05_CRIT_d: true$' && echo 1 || echo 0)" "real judge_v05 response file: (a)-(d) all parsed true from a real response file: $OUT3"
ok "$([ $rc3 -eq 0 ] && echo "$OUT3" | grep -q '^V05_RESULT: PASS$' && echo 1 || echo 0)" "real judge_v05 response + short-sentence draft: overall PASS, rc=0 (rc=$rc3)"
ok "$([ -f "${D3}.v05-judgment-request.txt" ] && echo 1 || echo 0)" "the judgment-request artifact was actually written for the running agent to read"

# missing/absent response file -> fail-closed to FAIL, never PASS (even though (e) alone would be true)
T4="$(mktemp -d)"
D4="$T4/draft.md"
cp "$D" "$D4"
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT4="$(bash "$SKILL/gates/v05.sh" "$D4" 2>&1)"; rc4=$?
ok "$([ $rc4 -ne 0 ] && echo 1 || echo 0)" "no judge_v05 response present: fail-closed, rc!=0 (rc=$rc4)"
ok "$(echo "$OUT4" | grep -q '^V05_RESULT: FAIL$' && echo 1 || echo 0)" "no judge_v05 response present: V05_RESULT: FAIL (never PASS even though (e) alone is true)"
ok "$(echo "$OUT4" | grep -q '^V05_CRIT_a: false$' && echo "$OUT4" | grep -q '^V05_CRIT_b: false$' && echo "$OUT4" | grep -q '^V05_CRIT_c: false$' && echo "$OUT4" | grep -q '^V05_CRIT_d: false$' && echo 1 || echo 0)" "no judge_v05 response present: (a)-(d) all fail closed to false (real parser never silently assumes PASS)"

# response file present but referring to a missing path -> still fail-closed (ARTICLE_JUDGE_V05_RESPONSE set
# to a nonexistent file must behave the same as unset, never crash / never silently PASS)
T5="$(mktemp -d)"
D5="$T5/draft.md"
cp "$D" "$D5"
unset ARTICLE_TEST_FORCE_V05
OUT5="$(ARTICLE_JUDGE_V05_RESPONSE="$T5/does-not-exist.txt" bash "$SKILL/gates/v05.sh" "$D5" 2>&1)"; rc5=$?
ok "$([ $rc5 -ne 0 ] && echo 1 || echo 0)" "ARTICLE_JUDGE_V05_RESPONSE points at a missing file: fail-closed, rc!=0 (rc=$rc5)"
ok "$(echo "$OUT5" | grep -q '^V05_RESULT: FAIL$' && echo 1 || echo 0)" "ARTICLE_JUDGE_V05_RESPONSE points at a missing file: V05_RESULT: FAIL"

[ $fails -eq 0 ] && { echo "PASS — real (non-FORCE) gates/v05.sh mechanics (readability arithmetic + judge_v05 parser)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
