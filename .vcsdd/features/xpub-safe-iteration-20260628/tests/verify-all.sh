#!/usr/bin/env bash
# verify-all.sh — Layer 1 grep + Layer 2 E2E runs. Exits 0 only if EVERY
# step passes. No X publish. No network beyond local filesystem.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS=~/.claude/skills/x-article-publisher/scripts

echo "=== L1 source greps ==="

grep -nE 'ImageOps\.exif_transpose\(img\)' "$SCRIPTS/copy_to_clipboard.py" > /dev/null
echo "  L1 OK: ImageOps.exif_transpose(img) present in compress_image"

grep -nE 'def load_exif_corrected_bytes' "$SCRIPTS/copy_to_clipboard.py" > /dev/null
echo "  L1 OK: load_exif_corrected_bytes helper defined"

grep -nE -- '--dry-write' "$SCRIPTS/copy_to_clipboard.py" > /dev/null
echo "  L1 OK: --dry-write flag declared"

grep -c 'consecutive_anchor_collision' "$SCRIPTS/parse_markdown.py" | { read n; [ "$n" -ge 2 ]; } \
  && echo "  L1 OK: consecutive_anchor_collision referenced multiple times" \
  || { echo "  L1 FAIL: consecutive_anchor_collision count < 2"; exit 1; }

grep -nE 'if not args\.no_cleanup_duplicates:' "$SCRIPTS/publish_md_to_x.py" > /dev/null
echo "  L1 OK: --no-cleanup-duplicates gate in place"

grep -nE 'POST-COND WARN.*DELETING via' "$SCRIPTS/publish_md_to_x.py" > /dev/null
echo "  L1 OK: WARN→delete branch present (load-bearing string)"

python3 -m py_compile "$SCRIPTS/replace_image_in_draft.py"
echo "  L1 OK: replace_image_in_draft.py py_compile clean"

python3 -m py_compile "$SCRIPTS/_xpub_browser.py"
echo "  L1 OK: _xpub_browser.py py_compile clean"

grep -nE 'compose/articles/edit/' "$SCRIPTS/replace_image_in_draft.py" > /dev/null
echo "  L1 OK: URL guard substring in replace_image_in_draft.py"

# Both delete_image_block call sites
publish_calls=$(grep -c 'delete_image_block' "$SCRIPTS/publish_md_to_x.py" || true)
replace_calls=$(grep -c 'delete_image_block' "$SCRIPTS/replace_image_in_draft.py" || true)
def_count=$(grep -c '^def delete_image_block' "$SCRIPTS/_xpub_browser.py" || true)
if [ "$publish_calls" -lt 1 ] || [ "$replace_calls" -lt 1 ] || [ "$def_count" -lt 1 ]; then
  echo "  L1 FAIL: delete_image_block — defs=$def_count, publish_calls=$publish_calls, replace_calls=$replace_calls"
  exit 1
fi
echo "  L1 OK: delete_image_block defined once + called from publish + replace"

# Callers must CHECK the return value (= adversary r2: silent paste on
# delete-fail produced duplicates).
grep -nE 'delete_image_block\([^)]*\)' "$SCRIPTS/replace_image_in_draft.py" | grep -qE 'if not delete_image_block|if not (\w+)' \
  && echo "  L1 OK: replace_image_in_draft.py checks delete_image_block return" \
  || { grep -nE 'if not delete_image_block' "$SCRIPTS/replace_image_in_draft.py" > /dev/null && echo "  L1 OK: replace_image_in_draft.py checks delete_image_block return" || { echo "  L1 FAIL: replace_image_in_draft.py ignores delete_image_block return value"; exit 1; } ; }

grep -nE 'delete_ok = delete_image_block|if not delete_ok' "$SCRIPTS/publish_md_to_x.py" > /dev/null \
  && echo "  L1 OK: publish_md_to_x.py checks delete_image_block return (WARN-retry branch)" \
  || { echo "  L1 FAIL: publish_md_to_x.py ignores delete_image_block return"; exit 1; }

# FM-1 regression grep: retry-coord-recompute must still be in place.
grep -nE 'RETRY re-targeted @' "$SCRIPTS/publish_md_to_x.py" > /dev/null \
  && echo "  L1 OK: FM-1 regression — retry coord recompute message present" \
  || { echo "  L1 FAIL: FM-1 regression — retry coord recompute log line missing"; exit 1; }

echo ""
echo "=== L2 NO-MOCK E2E ==="

python3 "$HERE/e1_exif.py"
python3 "$HERE/e2_consec.py"
bash "$HERE/e3_flag.sh"
bash "$HERE/e4_replace.sh"
bash "$HERE/e5_skills.sh"

echo ""
echo "=== ALL PASS ==="
