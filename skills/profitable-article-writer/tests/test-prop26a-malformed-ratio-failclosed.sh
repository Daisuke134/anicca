#!/usr/bin/env bash
# VSDD oracle -- PROP-26 (REQ-25, Sprint 4), malformed-ratio fail-closed: missing/uninitialized, N=0,
# negative N, and non-integer N EACH resolve to Mode A (never Mode B, never a crash) -- 4 distinct tested
# cases, per REQ-25's explicit enumeration.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# run_case: writes "T\nrc\nout..." to $3 (a result file) -- run directly (not via command substitution) so
# the wake's own rc/output survive outside any subshell.
run_case() {
  local ratio_content="$1" set_file="$2" resultfile="$3"
  local T; T="$(mktemp -d)"; mkdir -p "$T/state"
  [ "$set_file" = "yes" ] && printf '%s' "$ratio_content" > "$T/state/mode-b-ratio"
  local out rc
  out="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    timeout 10 bash "$SKILL/run.sh" 2>&1)"; rc=$?
  { printf '%s\n%s\n' "$T" "$rc"; printf '%s\n' "$out"; } > "$resultfile"
}

check_case() {
  local label="$1" resultfile="$2"
  local T rc
  T="$(sed -n '1p' "$resultfile")"
  rc="$(sed -n '2p' "$resultfile")"
  ok "$([ "$rc" = "0" ] && echo 1 || echo 0)" "$label -> wake completes rc=0, never crashes (rc=$rc)"
  ok "$(grep -q 'last_wake_result: DRAFT' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "$label -> resolves to Mode A (DRAFT, never PUBLISHED/UNCONFIRMED)"
}

R1="$(mktemp)"; run_case "" no "$R1"
check_case "case 1 (missing/uninitialized ratio)" "$R1"

R2="$(mktemp)"; run_case "0" yes "$R2"
check_case "case 2 (N=0)" "$R2"

R3="$(mktemp)"; run_case "-3" yes "$R3"
check_case "case 3 (N=-3, negative)" "$R3"

R4="$(mktemp)"; run_case "three" yes "$R4"
check_case "case 4 (N='three', non-integer)" "$R4"

[ $fails -eq 0 ] && { echo "PASS -- PROP-26 (REQ-25) all 4 malformed-ratio cases fail closed to Mode A, no crash"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
