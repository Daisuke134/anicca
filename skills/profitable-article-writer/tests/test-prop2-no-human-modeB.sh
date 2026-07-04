#!/usr/bin/env bash
# VSDD oracle — PROP-2 (REQ-2, REQ-13): the Mode-B path (AUTONOMY=on) has NO human-gating call. Mode A's
# review gate is explicitly EXCLUDED from this check (an intentional, temporary bootstrap — REQ-6).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: no unconditional interactive read/prompt in run.sh ----------
src="$(cat "$SKILL/run.sh")"
ok "$(grep -qE '^[[:space:]]*read[[:space:]]' <<<"$src" && echo 0 || echo 1)" "no unconditional interactive 'read' in run.sh"

# ---------- DYNAMIC: Mode B wake never blocks, never waits for a human, completes deterministically ----------
# Sprint-4 (REQ-25/PROP-26) update: effective mode is now ratio-derived, not a raw AUTONOMY read in
# isolation -- ARTICLE_MODEB_RATIO=1 ("1-in-1", every wake is Mode B) makes AUTONOMY=on reach Mode B here,
# same as this test always intended; PROP-26's own test suite covers the ratio-consultation mechanics.
T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_MODEB_RATIO=1 ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" timeout 10 bash "$SKILL/run.sh" </dev/null 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "Mode B wake completes with no human gate, rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'last_wake_result: PUBLISHED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "Mode B wake result is PUBLISHED (autonomous, no notify-and-wait)"
ok "$(! grep -qi 'notify_path' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "Mode B STATE has no Mode-A-style 'notify human' entry"

[ $fails -eq 0 ] && { echo "PASS — PROP-2 Mode B has no human-gating call"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
