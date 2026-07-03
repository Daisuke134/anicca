#!/usr/bin/env bash
# VSDD oracle — PROP-1 (REQ-1): the skill is model-agnostic. No provider-prefixed model id or API-key env
# name anywhere in the skill tree, AND a real end-to-end wake (not just a static grep) confirms the
# produced artifact is literal-free too.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: provider-prefixed model ids / API-key env names, anywhere in the skill tree ----------
FORBIDDEN='ANTHROPIC_API_KEY|OPENAI_API_KEY|XAI_API_KEY|DEEPSEEK_API_KEY|GOOGLE_API_KEY|GEMINI_API_KEY|claude-[0-9a-z-]*[0-9]|gpt-[0-9]|sk-ant-|sk-proj-|claude-sonnet|claude-opus|grok-[0-9]'
hits="$(grep -rEn "$FORBIDDEN" "$SKILL" --include='*.sh' --include='*.md' 2>/dev/null | grep -v '/tests/' || true)"
ok "$([ -z "$hits" ] && echo 1 || echo 0)" "PROP-1 static: 0 provider-prefixed model/API-key literals in skill tree (found: ${hits:-none})"

# ---------- DYNAMIC: a real wake (the checker ACTUALLY RUNS, not just a grep) must complete and its
# ---------- artifact must ALSO be literal-free ----------
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "PROP-1 dynamic: a real wake completes (rc=$rc): $OUT"
draft="$(grep -oE '^draft_path: .*' "$T/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -n "$draft" ] && [ -f "$draft" ] && echo 1 || echo 0)" "PROP-1 dynamic: wake produced a draft artifact to literal-check"
if [ -n "$draft" ] && [ -f "$draft" ]; then
  dhits="$(grep -Ec "$FORBIDDEN" "$draft" 2>/dev/null)"; dhits="${dhits:-0}"
  ok "$([ "$dhits" = 0 ] && echo 1 || echo 0)" "PROP-1 dynamic: produced draft contains 0 model/API-key literals"
fi

[ $fails -eq 0 ] && { echo "PASS — PROP-1 model-agnostic (static tree + dynamic wake artifact)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
