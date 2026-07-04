#!/usr/bin/env bash
# VSDD oracle -- PROP-26 (REQ-25, Sprint 4), contract-review FIND-001/FIND-002 fix verification: a
# leading-zero digit string (e.g. "08", "09", "1-in-08") passes run.sh's own "^[0-9]+$"/"^1-in-([0-9]+)$"
# regexes as syntactically valid, but bash's arithmetic evaluator ($(( )) / numeric "[ -eq ]") parses a
# leading-zero digit string as OCTAL -- and "8"/"9" are not valid octal digits, so a naive implementation
# raises a runtime "bash: ...: value too great for base" error (a crash/stderr leak) instead of a clean
# fail-closed. Same hazard applies to the wake-counter file. This test proves:
#   (1) N="08", N="09", "1-in-08" -- no crash, no raw bash arithmetic error text on stderr.
#   (2) a wake-counter file containing a leading-zero value ("08") is base-10-normalized to its correct
#       numeric value (8), same as a ratio value -- NOT crashed, and not corrupted/reset (the digit-only
#       sanitizer only resets on a genuinely non-digit value; a leading-zero digit string is a legitimate
#       counter reading once normalized, e.g. produced by re-reading a file this same function itself wrote
#       on a bash version/locale that could zero-pad -- so it increments correctly (8 -> 9) rather than
#       silently discarding wake-count history by resetting to 0).
#   (3) POSITIVE case: a leading-zero ratio that IS a legitimate value once base-10-normalized ("1-in-04",
#       i.e. decimal 4) is handled CORRECTLY end-to-end -- not merely "doesn't crash" but produces the
#       EXACT SAME N-1 Mode-A + 1 Mode-B cycle a plain "1-in-4" would (test-prop26c's own oracle), proving
#       leading-zero digit strings are deliberately base-10-normalized (never rejected as unconditionally
#       malformed, never octal-misparsed).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# run_case: writes "T\nrc\nout..." to $3 -- run directly (not via command substitution) so rc/stderr survive
# outside any subshell (same convention as test-prop26a).
run_case() {
  local ratio_content="$1" set_ratio_file="$2" counter_content="$3" resultfile="$4"
  local T; T="$(mktemp -d)"; mkdir -p "$T/state"
  [ "$set_ratio_file" = "yes" ] && printf '%s' "$ratio_content" > "$T/state/mode-b-ratio"
  [ -n "$counter_content" ] && printf '%s' "$counter_content" > "$T/state/mode-b-wake-count"
  local out rc
  out="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    timeout 10 bash "$SKILL/run.sh" 2>&1)"; rc=$?
  { printf '%s\n%s\n' "$T" "$rc"; printf '%s\n' "$out"; } > "$resultfile"
}

no_octal_crash_text() {
  # bash's own octal-misparse error text; MUST be absent from combined stdout+stderr.
  local out="$1"
  ! printf '%s' "$out" | grep -qiE 'value too great for base|invalid octal'
}

check_case() {
  local label="$1" resultfile="$2" expect_result="$3"
  local T rc out
  T="$(sed -n '1p' "$resultfile")"
  rc="$(sed -n '2p' "$resultfile")"
  out="$(tail -n +3 "$resultfile")"
  ok "$([ "$rc" = "0" ] && echo 1 || echo 0)" "$label -> wake completes rc=0, never crashes (rc=$rc)"
  ok "$(no_octal_crash_text "$out" && echo 1 || echo 0)" "$label -> no raw bash octal-misparse error text leaked to output/stderr"
  ok "$(grep -q "last_wake_result: $expect_result" "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "$label -> resolves to $expect_result"
}

# --- Case 1: N="08" (single fresh wake -> wake_n=1, normalized ratio=8, 1%8=1 -> Mode A/DRAFT) ---
R1="$(mktemp)"; run_case "08" yes "" "$R1"
check_case "case 1 (ARTICLE_MODEB_RATIO='08')" "$R1" "DRAFT"

# --- Case 2: N="09" (same reasoning, normalized ratio=9) ---
R2="$(mktemp)"; run_case "09" yes "" "$R2"
check_case "case 2 (ARTICLE_MODEB_RATIO='09')" "$R2" "DRAFT"

# --- Case 3: "1-in-08" (the 1-in-N string form with a leading-zero N) ---
R3="$(mktemp)"; run_case "1-in-08" yes "" "$R3"
check_case "case 3 (ARTICLE_MODEB_RATIO='1-in-08')" "$R3" "DRAFT"

# --- Case 4: wake-counter file holding a leading-zero value ("08") alongside a valid ratio (5) -- the
#     counter must base-10-normalize "08" -> 8, then increment to 9 (never crash, never octal-misparse).
#     9 % 5 = 4 != 0, so this wake correctly resolves to Mode A (DRAFT) -- NOT because the counter was
#     corrupted/reset, but because 9 genuinely is not a multiple of 5.
R4="$(mktemp)"; run_case "5" yes "08" "$R4"
check_case "case 4 (wake-counter file='08', ratio=5)" "$R4" "DRAFT"
T4="$(sed -n '1p' "$R4")"
ok "$([ "$(cat "$T4/state/mode-b-wake-count" 2>/dev/null)" = "9" ] && echo 1 || echo 0)" "case 4 -> leading-zero counter '08' base-10-normalizes to 8 then increments to 9 (got '$(cat "$T4/state/mode-b-wake-count" 2>/dev/null)'), not corrupted/reset"

# --- Case 5 (POSITIVE): "1-in-04" (decimal 4, written with a leading zero) run over a full 4-wake cycle --
#     MUST produce the exact same N-1 Mode-A + 1 Mode-B pattern test-prop26c proves for a plain "1-in-4",
#     proving the leading zero is deliberately normalized to its correct numeric value, not treated as
#     unconditionally malformed and not octal-misparsed.
N=4
T5="$(mktemp -d)"; mkdir -p "$T5/state"
printf '1-in-0%d' "$N" > "$T5/state/mode-b-ratio"
results=()
combined_out=""
for i in $(seq 1 "$N"); do
  out="$(ARTICLE_TEST=1 ARTICLE_DIR="$T5" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    timeout 10 bash "$SKILL/run.sh" 2>&1)"
  combined_out="$combined_out
$out"
  r="$(grep -oE '^last_wake_result: .*' "$T5/STATE.md" 2>/dev/null | sed 's/^last_wake_result: //')"
  results+=("$r")
done
ok "$(no_octal_crash_text "$combined_out" && echo 1 || echo 0)" "case 5 (positive, '1-in-04' over $N wakes) -> no raw bash octal-misparse error text anywhere in the $N-wake cycle"
modeA=0; modeB=0
for r in "${results[@]}"; do
  [ "$r" = "DRAFT" ] && modeA=$((modeA + 1))
  { [ "$r" = "PUBLISHED" ] || [ "$r" = "UNCONFIRMED" ]; } && modeB=$((modeB + 1))
done
ok "$([ "$modeA" -eq $((N - 1)) ] && echo 1 || echo 0)" "case 5 (positive) -> '1-in-04' normalizes to decimal 4 -> exactly $((N - 1)) Mode-A wakes over $N, got $modeA (sequence: ${results[*]})"
ok "$([ "$modeB" -eq 1 ] && echo 1 || echo 0)" "case 5 (positive) -> '1-in-04' normalizes to decimal 4 -> exactly 1 Mode-B wake over $N, got $modeB (sequence: ${results[*]})"
ok "$([ "${results[$((N - 1))]}" != "DRAFT" ] && echo 1 || echo 0)" "case 5 (positive) -> the 4th (last) wake in this fresh cycle is the Mode-B one, matching plain '1-in-4' behavior exactly (sequence: ${results[*]})"

[ $fails -eq 0 ] && { echo "PASS -- FIND-001/FIND-002 fix: leading-zero ratio/wake-counter values fail closed cleanly where malformed, and normalize CORRECTLY (never octal-misparsed) where they are a legitimate value"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
