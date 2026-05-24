#!/usr/bin/env bash
# anicca-tomb-slideshow-ja — daily 6-slide TikTok draft pipeline.
# Pipeline:
#   1. Pick today's product (rotation by day-of-week, override via PRODUCT env)
#   2. Generate 2 AI model images (male + female) wearing the product (fal.ai flux-dev)
#   3. Compose 6 slides with Pillow (impermanence narrative + product + price + URL)
#   4. Upload slides to Postiz CDN
#   5. POST to /public/v1/posts (drafts mode → @anicca.jpx TikTok)
#   6. Slack #metrics announce
#
# Final stdout line:
#   ✅ slideshow drafted: <slug> | postiz post=<id> | slides=<n> | slack ts=<ts>
#   ❌ slideshow FAILED: <reason>

set -euo pipefail

set -a; source ~/.openclaw/.env; set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-tomb-slideshow-ja"
PYTHON="python3"

DATE=$(date +%Y-%m-%d)
DOW=$(date +%u)  # 1-7
PRODUCT="${PRODUCT:-}"
if [ -z "$PRODUCT" ]; then
  PRODUCT=$($PYTHON -c "import json,sys;print(json.load(open('$SKILL_DIR/data/products.json'))['rotation']['$DOW'])")
fi
SLOT="${SLOT:-$(date +%H%M)}"
RUN_DIR="$SKILL_DIR/output/${DATE}_${PRODUCT}_${SLOT}"
mkdir -p "$RUN_DIR/images" "$RUN_DIR/slides"

echo "=== anicca-tomb-slideshow-ja run ==="
echo "  date=$DATE dow=$DOW product=$PRODUCT slot=$SLOT"
echo "  out=$RUN_DIR"
echo ""

# Step 1+2: AI model images + slide composition (single Python entrypoint for atomicity)
$PYTHON "$SKILL_DIR/scripts/build-slideshow.py" "$PRODUCT" "$RUN_DIR" || {
  echo "❌ slideshow FAILED: build-slideshow.py error"
  exit 1
}

# Step 3+4: Upload + Postiz draft
$PYTHON "$SKILL_DIR/scripts/postiz-draft.py" "$PRODUCT" "$RUN_DIR" || {
  echo "❌ slideshow FAILED: postiz-draft.py error"
  exit 1
}
