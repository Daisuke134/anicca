#!/usr/bin/env bash
# VSDD oracle — Sprint-2 contract-review FIND-003 fix: run.sh's generate_draft real-content hook must
# distinguish "ARTICLE_REAL_DRAFT_PATH supplied but the file does not exist" (a genuine wiring ERROR — a
# typo, a race, or a real daily-executor bug) from "no draft path supplied at all" (state (b)'s documented,
# intentional wiring safety-net). Both currently fall back to the SAME boilerplate content, but only the
# former must ALSO record a clearly-labeled failure line to state/failures.jsonl.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

BOILERPLATE_MARKER="burn 10+ hours"

# ---------- (1) ARTICLE_REAL_DRAFT_PATH SUPPLIED but points at a file that does NOT exist ----------
T="$(mktemp -d)"
MISSING_PATH="$T/does-not-exist-$(date +%s).md"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_TEST_V0_RESULTS ARTICLE_TEST_V05_RESULTS
OUT="$(ARTICLE_DIR="$T" AUTONOMY=off ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient ARTICLE_REAL_DRAFT_PATH="$MISSING_PATH" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "supplied-but-missing draft path: wake still completes cleanly, rc=0 (never crashes) (rc=$rc): $OUT"
ok "$([ -f "$T/draft.md" ] && grep -qF "$BOILERPLATE_MARKER" "$T/draft.md" && echo 1 || echo 0)" "supplied-but-missing draft path: still degrades to the boilerplate safety-net (never an empty/missing draft.md)"
ok "$(echo "$OUT" | grep -q 'WIRING ERROR' && echo 1 || echo 0)" "supplied-but-missing draft path: stderr carries an explicit WIRING ERROR diagnostic (distinct from the silent state-(b) fallback)"
ok "$([ -f "$T/state/failures.jsonl" ] && echo 1 || echo 0)" "supplied-but-missing draft path: state/failures.jsonl was written"
ok "$(grep -q 'generate_draft_wiring_error' "$T/state/failures.jsonl" 2>/dev/null && echo 1 || echo 0)" "supplied-but-missing draft path: failures.jsonl contains a distinct 'generate_draft_wiring_error' entry"
ok "$(grep -qF "$MISSING_PATH" "$T/state/failures.jsonl" 2>/dev/null && echo 1 || echo 0)" "failures.jsonl entry names the actual missing path, for real debuggability"

# ---------- (2) control: state (b), NO draft path supplied at all -> the SAME boilerplate content, but
# NO wiring-error entry (this is the documented, intentional safety-net, not a bug) ----------
T2="$(mktemp -d)"
unset ARTICLE_TEST ARTICLE_TEST_TOPIC ARTICLE_TEST_RESEARCH ARTICLE_REAL_DRAFT_PATH
OUT2="$(ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_REAL_TOPIC="x402" ARTICLE_REAL_RESEARCH=sufficient bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "control (no path at all): wake completes cleanly, rc=0 (rc=$rc2)"
ok "$([ -f "$T2/draft.md" ] && grep -qF "$BOILERPLATE_MARKER" "$T2/draft.md" && echo 1 || echo 0)" "control (no path at all): also falls back to the same boilerplate content"
ok "$(! echo "$OUT2" | grep -q 'WIRING ERROR' && echo 1 || echo 0)" "control (no path at all): NO 'WIRING ERROR' diagnostic (this is the intentional, non-error safety-net state)"
ok "$([ ! -f "$T2/state/failures.jsonl" ] || ! grep -q 'generate_draft_wiring_error' "$T2/state/failures.jsonl" && echo 1 || echo 0)" "control (no path at all): NO 'generate_draft_wiring_error' entry (distinct from the supplied-but-missing case)"

[ $fails -eq 0 ] && { echo "PASS — FIND-003 fix: supplied-but-missing ARTICLE_REAL_DRAFT_PATH is logged as a distinct wiring error, unlike the intentional no-path safety-net"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
