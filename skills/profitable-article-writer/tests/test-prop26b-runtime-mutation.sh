#!/usr/bin/env bash
# VSDD oracle -- PROP-26 (REQ-25, Sprint 4), runtime mutation: changing the ratio config VALUE for the SAME
# install ($ARTICLE_DIR, no code change/redeploy) changes wake behavior between consecutive invocations.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"; mkdir -p "$T/state"

wake() {
  ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" \
    ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS=PASS ARTICLE_TEST_V05_RESULTS=PASS \
    bash "$SKILL/run.sh" >/dev/null 2>&1
  grep -oE '^last_wake_result: .*' "$T/STATE.md" 2>/dev/null | sed 's/^last_wake_result: //'
}

# 1. no ratio config yet -> Mode A
rm -f "$T/state/mode-b-ratio" "$T/state/mode-b-wake-count"
R1="$(wake)"
ok "$([ "$R1" = "DRAFT" ] && echo 1 || echo 0)" "no ratio config -> Mode A (DRAFT), got '$R1'"

# 2. mutate the SAME running install's config FILE at runtime -- no redeploy, no code change -- to ratio=1
#    (every wake is Mode B).
rm -f "$T/state/mode-b-wake-count"
printf '1' > "$T/state/mode-b-ratio"
R2="$(wake)"
ok "$([ "$R2" = "PUBLISHED" ] && echo 1 || echo 0)" "AFTER mutating the ratio file at runtime (no redeploy) -> the SAME install now resolves Mode B ('$R2')"

# 3. mutate it BACK to a value that fails closed -> Mode A again, still no redeploy.
printf '0' > "$T/state/mode-b-ratio"
R3="$(wake)"
ok "$([ "$R3" = "DRAFT" ] && echo 1 || echo 0)" "mutating the ratio back to a malformed value (0) at runtime -> Mode A again ('$R3'), no redeploy needed"

# 4. mutate it forward again to a different valid N (2) -- proves the mutation is genuinely re-read each
#    wake, not cached/fixed at first-read.
rm -f "$T/state/mode-b-wake-count"
printf '2' > "$T/state/mode-b-ratio"
R4a="$(wake)"   # wake 1 of 2 -> Mode A
R4b="$(wake)"   # wake 2 of 2 -> Mode B
ok "$([ "$R4a" = "DRAFT" ] && [ "$R4b" = "PUBLISHED" ] && echo 1 || echo 0)" "mutating to ratio=2 at runtime -> wake 1 Mode A ('$R4a'), wake 2 Mode B ('$R4b')"

[ $fails -eq 0 ] && { echo "PASS -- PROP-26 runtime mutation: changing the ratio config value changes wake behavior with no redeploy"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
