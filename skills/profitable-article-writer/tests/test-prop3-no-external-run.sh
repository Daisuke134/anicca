#!/usr/bin/env bash
# VSDD oracle — PROP-3 (REQ-3): the article write-path makes NO external-repo/tool execution call
# (deterministic, static trace). The semantic "no claim of having run" check lives in V0.5 criterion (d)
# (REQ-5) — a defined binary check, not a keyword blocklist; exercised here only via the produced draft.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: no external-repo/tool execution pattern anywhere in the skill tree ----------
EXEC_PATTERNS='git clone|npm install|pip install|pip3 install|docker run|curl [^|]*\| *bash|eval "\$\(curl|wget .*\| *bash|npx '
hits="$(grep -rEn "$EXEC_PATTERNS" "$SKILL" --include='*.sh' 2>/dev/null | grep -v '/tests/' || true)"
ok "$([ -z "$hits" ] && echo 1 || echo 0)" "no external-repo/tool execution pattern in the skill tree (found: ${hits:-none})"

# ---------- DYNAMIC: a real wake produces an artifact whose body never claims to have executed anything ----------
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "a real wake completes so the write-path can be traced (rc=$rc): $OUT"
draft="$(grep -oE '^draft_path: .*' "$T/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -n "$draft" ] && [ -f "$draft" ] && echo 1 || echo 0)" "wake produced a draft artifact to trace"
if [ -n "$draft" ] && [ -f "$draft" ]; then
  ok "$(! grep -qiE 'i (ran|executed|cloned)|running the (repo|script|tool)|error-log:|stack trace' "$draft" && echo 1 || echo 0)" "draft never claims to have executed anything (REQ-3)"
fi

[ $fails -eq 0 ] && { echo "PASS — PROP-3 no external-repo/tool execution, no run-claims"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
