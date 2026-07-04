#!/usr/bin/env bash
# VSDD oracle — PROP-18 (REQ-5(e), Sprint 2): gates/v05.sh's real (non-FORCE) criterion-(e) readability
# arithmetic MUST split sentences on JAPANESE terminal punctuation (。！？), not only the ASCII '.','!','?'
# that tests/test-v05-real.sh exercises with English fixtures. REQ-19's daily executor writes a JAPANESE
# note DRAFT — if this gate only recognizes ASCII sentence-enders, a well-formed short-sentence Japanese
# draft (correctly punctuated with 。) collapses into a few giant multi-paragraph "sentences" (each far over
# 60 chars) and crit_e always computes false, permanently blocking Mode A for the one language this skill
# actually ships. This test proves the real (non-FORCE) mechanics handle Japanese punctuation correctly.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- (a) 4 individually-short JAPANESE sentences whose UNSPLIT concatenation exceeds 60 chars.
# This is the discriminating case: if the real splitter recognizes 。 as a boundary, each of the 4 sentences
# (~45 chars) is <=60 -> crit_e=true. If it does NOT (ASCII-only '.','!','?' splitter, the Sprint-1 bug),
# the whole 4-sentence paragraph collapses into ONE ~184-char "sentence" (well over 60) -> crit_e=false.
T="$(mktemp -d)"
D="$T/draft.md"
python3 - "$D" <<'PYEOF'
import sys
sentence = "これは四十五文字程度になるよう調整した短めの日本語の一文です。"
open(sys.argv[1], "w").write("# 短い文だけの日本語ドラフト\n\n" + sentence * 4 + "\n")
PYEOF
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT="$(bash "$SKILL/gates/v05.sh" "$D" 2>&1)"
ok "$(echo "$OUT" | grep -q '^V05_CRIT_e: true$' && echo 1 || echo 0)" "4 individually-short 。-terminated Japanese sentences (unsplit concatenation >60 chars): real (e) splits on 。 and computes crit_e=true: $OUT"

# ---------- (b) a genuinely long Japanese sentence (still 。-terminated) -> crit_e=false ----------
T2="$(mktemp -d)"
D2="$T2/draft.md"
python3 - "$D2" <<'PYEOF'
import sys
long_sentence = "これは" + "とても" * 30 + "長い一文です。"
short = "短い文です。"
open(sys.argv[1], "w").write(f"# 長い文のドラフト\n\n{long_sentence}{short}{short}\n")
PYEOF
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT2="$(bash "$SKILL/gates/v05.sh" "$D2" 2>&1)"
ok "$(echo "$OUT2" | grep -q '^V05_CRIT_e: false$' && echo 1 || echo 0)" "one very long Japanese sentence dominating a 3-sentence draft: real (e) computes crit_e=false: $OUT2"

# ---------- (c) mixed 。！？ terminal punctuation, each segment short but the unsplit concatenation >60 chars
# -> real (e) must recognize ALL THREE Japanese terminal marks as boundaries, not just 。
T3="$(mktemp -d)"
D3="$T3/draft.md"
python3 - "$D3" <<'PYEOF'
import sys
seg = "これは短い一文です" * 3  # ~27 chars, well under 60
body = seg + "。" + seg + "？" + seg + "！" + seg + "。"
open(sys.argv[1], "w").write("# 混在する終端記号\n\n" + body + "\n")
PYEOF
unset ARTICLE_TEST_FORCE_V05 ARTICLE_JUDGE_V05_RESPONSE
OUT3="$(bash "$SKILL/gates/v05.sh" "$D3" 2>&1)"
ok "$(echo "$OUT3" | grep -q '^V05_CRIT_e: true$' && echo 1 || echo 0)" "。！？ all recognized as sentence-enders (each segment short, unsplit concatenation >60 chars): real (e) computes crit_e=true: $OUT3"

[ $fails -eq 0 ] && { echo "PASS — PROP-18 real gates/v05.sh (e) recognizes Japanese sentence punctuation"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
