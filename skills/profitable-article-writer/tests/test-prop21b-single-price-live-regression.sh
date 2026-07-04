#!/usr/bin/env bash
# VSDD oracle -- FIND-005 fix (Sprint-3 contract review): a LIVE regression test for
# lib/note-set-single-price.py, the ORIGINAL caller of note_browser_common.select_paid_price() (extracted
# FROM this script's own inline block in Sprint 2.5 so lib/note-publish-live.py could reuse it -- see
# note_browser_common.py's own docstring and this script's own docstring: "Moving this here changes nothing
# observable about note-set-single-price.py's own stdout/behavior."). tests/test-prop21-visual-and-single-
# price.sh only proves this refactor structurally (grep + py_compile per its own header comment); it never
# executes note-set-single-price.py against a real browser session. This file proves the "unchanged
# behavior" claim LIVE, against a real note.com draft -- the one claim Sprint 2.5's own test suite never
# actually checked for note-set-single-price.py's call site specifically (test-prop22b only proved
# select_paid_price() still works through the NEW caller, lib/note-publish-live.py).
#
# Reuses the SAME TEST draft (ne94efe526c9a) test-prop22b/test-prop24c already exercise for the shared
# publish-click unit. note-set-single-price.py NEVER clicks 投稿する/更新する (it only sets
# 記事タイプ=有料/価格, screenshots the panel, then clicks キャンセル) -- see its own docstring's final
# line: "NEVER submits. No 投稿する/更新する click exists anywhere in this file." -- so re-running it
# against this draft (whether it is still 'draft' or already 'published' from a prior test-prop22b/
# test-prop24c run) is a safe, non-publishing, idempotent operation. The flagship draft (nfb2ace9f0ed8) is
# NEVER used here.
#
# Sprint-4 note: the ORIGINAL test draft (n39ef09f828f7) was found DELETED on note.com (external
# environment drift, unrelated to any code change here) -- ne94efe526c9a is its VCSDD-internal-test-only
# replacement, created via this skill's own reused note-create-rich-draft.py/note-set-eyecatch.py pipeline
# (never published outside this test suite's own mechanism checks).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
TOOL="$SKILL/lib/note-set-single-price.py"

# ★★★ SAFETY: hardcoded, literal keys -- this test may NEVER touch the flagship draft. ★★★
TEST_DRAFT_KEY="ne94efe526c9a"
FLAGSHIP_DRAFT_KEY="nfb2ace9f0ed8"
if [ "$TEST_DRAFT_KEY" = "$FLAGSHIP_DRAFT_KEY" ]; then
  echo "SAFETY ABORT: TEST_DRAFT_KEY must never equal FLAGSHIP_DRAFT_KEY" >&2
  exit 3
fi

fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

VENV_PY="$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3"
COOKIES_FILE="${NOTE_COOKIES_FILE:-$HOME/.cloak/note-work/note-cookies.json}"

if [ ! -x "$VENV_PY" ] || [ ! -f "$COOKIES_FILE" ]; then
  echo "SKIP -- real cloakbrowser/note.com-cookies environment not available on this host " \
       "(venv_py=$([ -x "$VENV_PY" ] && echo present || echo MISSING), " \
       "cookies=$([ -f "$COOKIES_FILE" ] && echo present || echo MISSING)) -- " \
       "FIND-005's live regression check cannot be hermetically stubbed for select_paid_price()'s real DOM " \
       "behavior."
  exit 0
fi

OUT="$(NOTE_COOKIES_FILE="$COOKIES_FILE" "$VENV_PY" "$TOOL" "$TEST_DRAFT_KEY" 500 "まとめ" 2>&1)"; RC=$?
echo "  tool output: $OUT"

ok "$([ $RC -eq 0 ] && echo 1 || echo 0)" "note-set-single-price.py against the REAL TEST draft $TEST_DRAFT_KEY -> rc=0 (rc=$RC), unchanged after the select_paid_price() extraction"
ok "$(echo "$OUT" | grep -q '^SINGLE_PRICE_TYPE: paid$' && echo 1 || echo 0)" "post-refactor DOM readback still confirms 記事タイプ=有料 (SINGLE_PRICE_TYPE: paid)"
ok "$(echo "$OUT" | grep -q '^SINGLE_PRICE_VALUE: 500$' && echo 1 || echo 0)" "post-refactor DOM readback still confirms 価格=500 (SINGLE_PRICE_VALUE: 500)"
PANEL_SHOT="$(echo "$OUT" | grep -oE 'SINGLE_PRICE_PANEL_SCREENSHOT: .*' | sed 's/^SINGLE_PRICE_PANEL_SCREENSHOT: //')"
ok "$([ -n "$PANEL_SHOT" ] && [ -f "$PANEL_SHOT" ] && [ -s "$PANEL_SHOT" ] && echo 1 || echo 0)" "the CRIT-105 panel screenshot (有料/¥500 visibly set on screen, captured BEFORE キャンセル) was written to disk and is non-empty: $PANEL_SHOT"
BODY_SHOT="$(echo "$OUT" | grep -oE '^SINGLE_PRICE_SCREENSHOT: .*' | sed 's/^SINGLE_PRICE_SCREENSHOT: //')"
ok "$([ -n "$BODY_SHOT" ] && [ -f "$BODY_SHOT" ] && [ -s "$BODY_SHOT" ] && echo 1 || echo 0)" "the post-cancel body screenshot was also written to disk and is non-empty (full flow completed, not just the panel step): $BODY_SHOT"
ok "$(! echo "$OUT" | grep -q "$FLAGSHIP_DRAFT_KEY" && echo 1 || echo 0)" "the flagship draft key never appears anywhere in this test's own tool output"
ok "$(! echo "$OUT" | grep -qE '投稿する|更新する' && echo 1 || echo 0)" "note-set-single-price.py's own output never mentions a 投稿する/更新する click (still never publishes, post-refactor)"

[ $fails -eq 0 ] && { echo "PASS -- FIND-005: note-set-single-price.py's call to the shared select_paid_price() is LIVE-regression-verified against TEST draft $TEST_DRAFT_KEY, no behavior change from the Sprint-2.5 extraction"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
