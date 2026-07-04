#!/usr/bin/env bash
# VSDD oracle — PROP-21 (REQ-3/8, Sprint 2 bugfix): the 3 real defects a fresh-context adversary found in
# the rendered draft (key n7261a753887f) must be structurally impossible to regress to:
#   1. NO VISUALS in the article body -> lib/note-create-rich-draft.py must exist and genuinely call
#      note_mcp's upload_body_image + generate_image_html + create_draft (not a stub/fake).
#   2. NO eyecatch/cover -> the same file must call note_mcp's upload_eyecatch_image.
#   3. Monetization wired to メンバーシップ (membership) instead of a single ¥500 有料note -> the WIRING
#      (lib/note_publish.sh) must never call the old membership-hardcoded `publish-to-note.sh publish`
#      subcommand any more, and lib/note-set-single-price.py must select 有料 and must NEVER contain a
#      投稿する/更新する click (the one thing that would make it capable of actually publishing).
# This is a structural/static oracle (grep + python -m py_compile) — it proves the WIRING is pointed at the
# right calls, not a live network/browser assertion (those require real creds; see Sprint-2 evidence dir).
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

RICH_DRAFT_PY="$SKILL/lib/note-create-rich-draft.py"
SINGLE_PRICE_PY="$SKILL/lib/note-set-single-price.py"
NOTE_PUBLISH_SH="$SKILL/lib/note_publish.sh"

# ---------- defect 1: visuals wiring exists and calls the REAL note_mcp API ----------
ok "$([ -f "$RICH_DRAFT_PY" ] && echo 1 || echo 0)" "lib/note-create-rich-draft.py exists"
ok "$(grep -q 'upload_body_image' "$RICH_DRAFT_PY" 2>/dev/null && echo 1 || echo 0)" "note-create-rich-draft.py calls note_mcp.upload_body_image (hero + inline figures)"
ok "$(grep -q 'generate_image_html' "$RICH_DRAFT_PY" 2>/dev/null && echo 1 || echo 0)" "note-create-rich-draft.py embeds images via note_mcp.generate_image_html (never plain markdown that note.com distorts to 620x457)"
ok "$(grep -q 'create_draft' "$RICH_DRAFT_PY" 2>/dev/null && echo 1 || echo 0)" "note-create-rich-draft.py calls note_mcp.create_draft (a genuinely new note.com draft, not a local-only file)"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 -m py_compile "$RICH_DRAFT_PY" 2>/dev/null && echo 1 || echo 0)" "note-create-rich-draft.py is syntactically valid Python"
fi

# ---------- defect 2: eyecatch/cover wiring exists (browser path -- the note_mcp API path is a confirmed
# live 'missing url' bug, verified 2026-07-04; see lib/note-set-eyecatch.py's own docstring) ----------
EYECATCH_PY="$SKILL/lib/note-set-eyecatch.py"
ok "$([ -f "$EYECATCH_PY" ] && echo 1 || echo 0)" "lib/note-set-eyecatch.py exists"
ok "$(grep -q '画像を追加' "$EYECATCH_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-eyecatch.py drives the editor's 画像を追加 (add image) button"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 -m py_compile "$EYECATCH_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-eyecatch.py is syntactically valid Python"
fi

# ---------- defect 3: single ¥500 有料note, never メンバーシップ ----------
ok "$([ -f "$SINGLE_PRICE_PY" ] && echo 1 || echo 0)" "lib/note-set-single-price.py exists"
ok "$(grep -q '有料' "$SINGLE_PRICE_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-single-price.py selects 有料 (single-price paid type)"
ok "$(! grep -q 'メンバーシップ' "$SINGLE_PRICE_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-single-price.py NEVER references メンバーシップ (no membership fallback path)"
ok "$(! grep -qE \"[\\x27\\\"]投稿する[\\x27\\\"]\" "$SINGLE_PRICE_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-single-price.py contains NO 投稿する click target (never reaches publish -- Mode A REQ-6 fail-closed)"
ok "$(! grep -qE \"[\\x27\\\"]更新する[\\x27\\\"]\" "$SINGLE_PRICE_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-single-price.py contains NO 更新する click target (never reaches publish)"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 -m py_compile "$SINGLE_PRICE_PY" 2>/dev/null && echo 1 || echo 0)" "note-set-single-price.py is syntactically valid Python"
fi

# ---------- the WIRING must no longer route through the old membership publish subcommand ----------
ok "$([ -f "$NOTE_PUBLISH_SH" ] && echo 1 || echo 0)" "lib/note_publish.sh exists"
ok "$(! grep -qE '\\$NOTE_PUBLISH_SCRIPT.? publish ' "$NOTE_PUBLISH_SH" 2>/dev/null && echo 1 || echo 0)" "lib/note_publish.sh no longer calls the old membership-hardcoded '\$NOTE_PUBLISH_SCRIPT publish' subcommand"
ok "$(grep -q 'note_create_rich_draft' "$NOTE_PUBLISH_SH" 2>/dev/null && echo 1 || echo 0)" "lib/note_publish.sh's run_note_mode_a_publish routes through note_create_rich_draft (visuals)"
ok "$(grep -q 'note_set_eyecatch' "$NOTE_PUBLISH_SH" 2>/dev/null && echo 1 || echo 0)" "lib/note_publish.sh's run_note_mode_a_publish routes through note_set_eyecatch (cover)"
ok "$(grep -q 'note_set_single_price' "$NOTE_PUBLISH_SH" 2>/dev/null && echo 1 || echo 0)" "lib/note_publish.sh's run_note_mode_a_publish routes through note_set_single_price (single ¥ gate, not membership)"

[ $fails -eq 0 ] && { echo "PASS — PROP-21 visuals+eyecatch+single-price wiring replaces the pure-text/membership defects"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
