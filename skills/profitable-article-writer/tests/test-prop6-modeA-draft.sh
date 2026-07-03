#!/usr/bin/env bash
# VSDD oracle — PROP-6 (REQ-6): Mode A (AUTONOMY=off, default) stops at a note DRAFT and notifies the
# human (URL + screenshot) for review; it SHALL NOT publish.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "Mode A wake completes, rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'last_wake_result: DRAFT' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "Mode A STATE result is DRAFT (not PUBLISHED)"
draft="$(grep -oE '^draft_path: .*' "$T/STATE.md" 2>/dev/null | sed 's/^draft_path: //')"
ok "$([ -n "$draft" ] && [ -f "$draft" ] && echo 1 || echo 0)" "Mode A produced a draft artifact"
notify="$(grep -oE '^notify_path: .*' "$T/STATE.md" 2>/dev/null | sed 's/^notify_path: //')"
ok "$([ -n "$notify" ] && [ -f "$notify" ] && echo 1 || echo 0)" "Mode A wrote a notify record (URL + screenshot) for human review"
ok "$([ -f "$notify" ] && grep -q '"url"' "$notify" && grep -q '"screenshot"' "$notify" && echo 1 || echo 0)" "Mode A notify record actually contains url + screenshot fields (CRIT-002)"
ok "$([ ! -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "Mode A NEVER publishes (no publish sentinel)"

[ $fails -eq 0 ] && { echo "PASS — PROP-6 Mode A stops at draft + notify, never publishes"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
