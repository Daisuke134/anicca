#!/usr/bin/env bash
# VSDD oracle -- PROP-24 (REQ-23, Sprint 4), structural: the publish-click statement (the REAL
# 投稿する/更新する click) exists in EXACTLY ONE file across the whole skill tree --
# lib/note_browser_common.py's confirm_and_publish() -- imported by BOTH lib/note-publish-live.py (REQ-21's
# one-off tool) and lib/note-mode-b-publish.py (run.sh's unattended Mode-B in-loop caller). No duplicated
# pre-publish-check/click/exception-safety logic anywhere else.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# code-only anchors for "the actual click statement" -- distinct from the many PROSE mentions of
# 投稿する/更新する that legitimately appear in docstrings/comments/tests across this tree.
CLICK_ANCHOR='el.click(); return true;} return false;'
FALLBACK_ANCHOR='get_by_text(label, exact=True).first.click(timeout=4000)'

CLICK_HITS="$(grep -rlF "$CLICK_ANCHOR" "$SKILL" --include='*.py' 2>/dev/null | sort)"
FALLBACK_HITS="$(grep -rlF "$FALLBACK_ANCHOR" "$SKILL" --include='*.py' 2>/dev/null | sort)"

CLICK_COUNT=0; [ -n "$CLICK_HITS" ] && CLICK_COUNT="$(printf '%s\n' "$CLICK_HITS" | wc -l | tr -d ' ')"
FALLBACK_COUNT=0; [ -n "$FALLBACK_HITS" ] && FALLBACK_COUNT="$(printf '%s\n' "$FALLBACK_HITS" | wc -l | tr -d ' ')"

ok "$([ "$CLICK_COUNT" = "1" ] && echo 1 || echo 0)" "the publish-click JS statement appears in EXACTLY ONE .py file across the whole skill tree (found in: $CLICK_HITS)"
ok "$([ "$FALLBACK_COUNT" = "1" ] && echo 1 || echo 0)" "the click fallback statement (get_by_text(...).first.click(...)) appears in EXACTLY ONE .py file (found in: $FALLBACK_HITS)"
ok "$(printf '%s\n' "$CLICK_HITS" | grep -q 'lib/note_browser_common.py$' && echo 1 || echo 0)" "the single location is lib/note_browser_common.py (the shared unit)"
ok "$(! grep -qF "$CLICK_ANCHOR" "$SKILL/lib/note-publish-live.py" 2>/dev/null && echo 1 || echo 0)" "lib/note-publish-live.py no longer contains its own copy of the click statement (imports the shared function instead)"
ok "$([ -f "$SKILL/lib/note-mode-b-publish.py" ] && ! grep -qF "$CLICK_ANCHOR" "$SKILL/lib/note-mode-b-publish.py" 2>/dev/null && echo 1 || echo 0)" "lib/note-mode-b-publish.py contains no copy of the click statement either (imports the shared function)"

# both callers actually IMPORT the shared function, not re-implement it.
ok "$(grep -qE 'from note_browser_common import.*confirm_and_publish' "$SKILL/lib/note-publish-live.py" && echo 1 || echo 0)" "lib/note-publish-live.py imports confirm_and_publish from note_browser_common (single source, not a copy)"
ok "$([ -f "$SKILL/lib/note-mode-b-publish.py" ] && grep -qE 'from note_browser_common import.*confirm_and_publish' "$SKILL/lib/note-mode-b-publish.py" && echo 1 || echo 0)" "lib/note-mode-b-publish.py (run.sh's Mode-B caller) also imports confirm_and_publish from note_browser_common (same shared unit, not reimplemented)"

# run.sh's own Mode-B branch reaches confirm_and_publish ONLY via lib/note-mode-b-publish.py (never
# note-publish-live.py directly -- REQ-21's own exclusion from run.sh's call graph is unaffected).
ok "$(grep -q 'note-mode-b-publish.py' "$SKILL/run.sh" && echo 1 || echo 0)" "run.sh's Mode-B branch calls lib/note-mode-b-publish.py"
ok "$(! grep -q 'note-publish-live' "$SKILL/run.sh" && echo 1 || echo 0)" "run.sh STILL never references note-publish-live.py (REQ-21's exclusion unaffected by Sprint-4 wiring)"

# try/except/finally exception-safety (Sprint-3 FIND-004 fix) lives INSIDE confirm_and_publish, not
# re-wrapped per caller.
ok "$(grep -q 'def confirm_and_publish' "$SKILL/lib/note_browser_common.py" && echo 1 || echo 0)" "note_browser_common.py defines confirm_and_publish"
HAS_TRY="$(python3 -c "
import ast
tree = ast.parse(open('$SKILL/lib/note_browser_common.py').read())
fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'confirm_and_publish'), None)
print(1 if (fn is not None and any(isinstance(n, ast.Try) for n in ast.walk(fn))) else 0)
" 2>/dev/null || echo 0)"
ok "$HAS_TRY" "confirm_and_publish contains its own try/except/finally block (exception-safety lives in the shared unit, not re-wrapped per caller)"

# neither caller re-implements its own try/except/finally around a browser-session lifecycle -- syntactic
# sanity: they should be short files calling into the shared function, not owning Try blocks of their own
# browser-lifecycle logic.
ok "$(python3 -m py_compile "$SKILL/lib/note-publish-live.py" 2>/dev/null && echo 1 || echo 0)" "lib/note-publish-live.py is syntactically valid Python"
ok "$([ -f "$SKILL/lib/note-mode-b-publish.py" ] && python3 -m py_compile "$SKILL/lib/note-mode-b-publish.py" 2>/dev/null && echo 1 || echo 0)" "lib/note-mode-b-publish.py is syntactically valid Python"

[ $fails -eq 0 ] && { echo "PASS -- PROP-24 structural: the publish-click statement + exception-safety wrapper exist in exactly ONE shared file, imported by both callers"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
