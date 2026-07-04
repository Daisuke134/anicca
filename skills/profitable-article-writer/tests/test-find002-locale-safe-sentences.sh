#!/usr/bin/env bash
# VSDD oracle — Sprint-2 contract-review FIND-002 fix: gates/v05.sh's real (non-FORCE) criterion-(e)
# sentence splitter must be LOCALE-SAFE. A byte-wise `tr '.!?。！？' ...` corrupts multi-byte Japanese
# terminal punctuation mid-character under a C/POSIX locale — the common default for a minimal/cron/
# headless environment, i.e. exactly the unattended `claude -p` daily-executor REQ-19 describes — because
# the individual UTF-8 bytes making up 。！？ also occur inside countless unrelated Japanese characters.
#
# This test proves TWO things on the SAME fixture (one genuinely-long 。-terminated Japanese sentence
# plus two short ones — correct verdict is crit_e=false, reusing tests/test-prop18's case (b) fixture):
#   1. CONTROL: the OLD byte-wise `tr` approach (reproduced verbatim below — it no longer exists in
#      gates/v05.sh after the FIND-002 fix, so it cannot be re-imported), run under `LC_ALL=C`, computes
#      the WRONG verdict (crit_e=true) — proving the byte-corruption failure mode is real, not theoretical.
#   2. FIX: the CURRENT gates/v05.sh (now python3-based, locale-independent), run under the exact same
#      `LC_ALL=C`, computes the CORRECT verdict (crit_e=false).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"
D="$T/draft.md"
python3 - "$D" <<'PYEOF'
import sys
long_sentence = "これは" + "とても" * 30 + "長い一文です。"
short = "短い文です。"
open(sys.argv[1], "w").write(f"# 長い文のドラフト\n\n{long_sentence}{short}{short}\n")
PYEOF

# ---------- 1. CONTROL: the OLD byte-wise `tr` splitter, forced under LC_ALL=C, on the SAME fixture ----------
body="$(cat "$D")"
plain="$(echo "$body" | grep -vE '^#' | grep -vE '^[[:space:]]*$')"
old_sentences="$(echo "$plain" | LC_ALL=C tr '.!?。！？' '\n\n\n\n\n\n' 2>/dev/null | LC_ALL=C sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' 2>/dev/null | LC_ALL=C grep -vE '^$' 2>/dev/null)"
old_total=0
old_short=0
while IFS= read -r s; do
  [ -z "$s" ] && continue
  old_total=$((old_total+1))
  len=${#s}
  if [ "$len" -le 60 ]; then old_short=$((old_short+1)); fi
done <<EOF
$old_sentences
EOF
old_pct=0
old_crit_e=false
if [ "$old_total" -gt 0 ]; then
  old_pct=$(( old_short * 100 / old_total ))
  [ "$old_pct" -ge 70 ] && old_crit_e=true
fi
ok "$([ "$old_crit_e" = "true" ] && echo 1 || echo 0)" "CONTROL: the old byte-wise tr splitter under LC_ALL=C gives the WRONG verdict (crit_e=true, old_total=$old_total old_short=$old_short old_pct=$old_pct%) on a genuinely-long Japanese sentence that should FAIL -- proving the byte-corruption failure mode is real"

# ---------- 2. FIX: the CURRENT gates/v05.sh, run under the SAME LC_ALL=C, on the SAME fixture ----------
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT="$(LC_ALL=C LANG=C bash "$SKILL/gates/v05.sh" "$D" 2>&1)"
ok "$(echo "$OUT" | grep -q '^V05_CRIT_e: false$' && echo 1 || echo 0)" "FIX: the CURRENT (locale-safe, python3-based) gates/v05.sh gives the CORRECT verdict (crit_e=false) under LC_ALL=C: $OUT"

[ $fails -eq 0 ] && { echo "PASS — FIND-002 fix: gates/v05.sh (e) is locale-safe, unlike the old byte-wise tr splitter"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
