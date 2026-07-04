#!/usr/bin/env bash
# VSDD oracle -- PROP-26 (REQ-25, Sprint 4), "1-in-N" end-to-end: setting the ratio to "1-in-N" actually
# produces EXACTLY N-1 Mode-A wakes and 1 Mode-B wake over N consecutive wakes -- not merely that the ratio
# value is stored.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

N=4
T="$(mktemp -d)"; mkdir -p "$T/state"
printf '1-in-%d' "$N" > "$T/state/mode-b-ratio"

results=()
for i in $(seq 1 "$N"); do
  ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    bash "$SKILL/run.sh" >/dev/null 2>&1
  r="$(grep -oE '^last_wake_result: .*' "$T/STATE.md" 2>/dev/null | sed 's/^last_wake_result: //')"
  results+=("$r")
done

modeA=0; modeB=0
for r in "${results[@]}"; do
  [ "$r" = "DRAFT" ] && modeA=$((modeA + 1))
  { [ "$r" = "PUBLISHED" ] || [ "$r" = "UNCONFIRMED" ]; } && modeB=$((modeB + 1))
done

ok "$([ "$modeA" -eq $((N - 1)) ] && echo 1 || echo 0)" "1-in-$N ratio -> exactly $((N - 1)) Mode-A (DRAFT) wakes over $N consecutive wakes, got $modeA (sequence: ${results[*]})"
ok "$([ "$modeB" -eq 1 ] && echo 1 || echo 0)" "1-in-$N ratio -> exactly 1 Mode-B wake over $N consecutive wakes, got $modeB (sequence: ${results[*]})"
ok "$([ "${results[$((N - 1))]}" != "DRAFT" ] && echo 1 || echo 0)" "the Nth (last) wake in this fresh cycle is the Mode-B one (sequence: ${results[*]})"

[ $fails -eq 0 ] && { echo "PASS -- PROP-26 1-in-N end-to-end: exactly N-1 Mode-A + 1 Mode-B over N consecutive wakes"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
