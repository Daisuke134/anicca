#!/usr/bin/env bash
# anicca-retreat-slideshow — daily 6-slide TikTok draft pipeline.
# Pipeline:
#   1. Pick today's theme by DOW (override via THEME=<slug>)
#   2. Build 6 typography slides (Pillow, no fal.ai)
#   3. Upload to Postiz CDN
#   4. POST /public/v1/posts as TikTok draft (@anicca.jpx until anicca.retreat warmup)
#   5. Slack #metrics announce
#
# Final stdout line:
#   ✅ retreat slideshow drafted: <theme> | postiz post=<id> | slides=6 | slack ts=<ts>

set -euo pipefail

if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; source "$HOME/.openclaw/.env"; set +a
fi

SKILL_DIR="$HOME/.openclaw/skills/anicca-retreat-slideshow"
PYTHON="python3"

DATE=$(date +%Y-%m-%d)
DOW=$(date +%u)  # 1-7
THEME="${THEME:-}"
if [ -z "$THEME" ]; then
  THEME=$($PYTHON -c "import json;print(json.load(open('$SKILL_DIR/data/themes.json'))['rotation']['$DOW'])")
fi
SLOT="${SLOT:-$(date +%H%M)}"
RUN_DIR="$SKILL_DIR/output/${DATE}_${THEME}_${SLOT}"
mkdir -p "$RUN_DIR/slides"

echo "=== anicca-retreat-slideshow run ==="
echo "  date=$DATE dow=$DOW theme=$THEME slot=$SLOT"
echo "  out=$RUN_DIR"
echo ""

# Step 1+2: Build slides (Pillow typography only)
$PYTHON "$SKILL_DIR/scripts/build-slides.py" "$THEME" "$RUN_DIR" || {
  echo "❌ retreat slideshow FAILED: build-slides.py error"
  exit 1
}

# Step 3+4: Upload + Postiz draft + Slack
$PYTHON "$SKILL_DIR/scripts/postiz-draft.py" "$THEME" "$RUN_DIR" || {
  echo "❌ retreat slideshow FAILED: postiz-draft.py error"
  exit 1
}
