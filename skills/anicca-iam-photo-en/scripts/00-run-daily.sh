#!/usr/bin/env bash
# anicca-iam-photo-en — daily Template A EN single-image TikTok draft.
set -euo pipefail
set -a; source ~/.openclaw/.env; set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-iam-photo-en"
DATE=$(date +%Y-%m-%d)
SLOT="${SLOT:-$(date +%H%M)}"
RUN_DIR="$SKILL_DIR/output/${DATE}_${SLOT}"
mkdir -p "$RUN_DIR/images" "$RUN_DIR/slides"

echo "=== anicca-iam-photo-en run ==="
echo "  date=$DATE slot=$SLOT out=$RUN_DIR"

python3 "$SKILL_DIR/scripts/build-slideshow.py" "$RUN_DIR" || { echo "❌ FAILED: build"; exit 1; }
python3 "$SKILL_DIR/scripts/postiz-draft.py" "$RUN_DIR" || { echo "❌ FAILED: postiz-draft"; exit 1; }
