#!/usr/bin/env bash
# Step 5+6 of article: Postiz REST API → TikTok Drafts (UPLOAD mode).
# Per article: NEVER direct-post (server-IP detection = ban). Always push to
# TikTok app Inbox via content_posting_method: "UPLOAD".
#
# IMPORTANT: Postiz CLI's `-m` flag does NOT correctly send multi-image
# slideshows to TikTok integration. Reference: Larry skill
# (skills-clawhub-compare/larry/scripts/post-to-tiktok.js) uses REST API
# directly with image:[{id,path}, ...] array — this is the proven pattern
# that successfully posts 6-slide drafts to TikTok daily.
#
# Usage:
#   06-postiz-publish.sh <slides_dir> <caption_file> <hashtags_file> [--dry-run]
#
# Writes: <slides_dir>/postiz-receipt.json (parent dir)

set -euo pipefail

SLIDES_DIR="$1"
CAPTION_FILE="$2"
HASHTAGS_FILE="$3"
DRY_RUN=false
if [ "${4:-}" = "--dry-run" ]; then DRY_RUN=true; fi

[ -z "${POSTIZ_API_KEY:-}" ] && { echo "ERR: POSTIZ_API_KEY not set" >&2; exit 3; }
[ -z "${POSTIZ_TIKTOK_INTEGRATION_ID:-}" ] && { echo "ERR: POSTIZ_TIKTOK_INTEGRATION_ID not set" >&2; exit 4; }
# === Fixed TikTok account (4.7 JA slideshow — canonical 2026-05-19, Dais final) ===
POSTIZ_TIKTOK_INTEGRATION_ID="cmp9sdev5012voh0y58qs45xc"  # 4.7 JA slideshow TikTok (canonical)
# === Fixed Instagram account (4.7 JA slideshow — canonical 2026-05-20, Dais final) ===
POSTIZ_IG_INTEGRATION_ID="cmn8ycvtn02djqx0ytuisn9mw"  # iam/mantra/4.7 JA slideshow Instagram (canonical)
echo "[fixed] tt-integration=cmp9sdev5012voh0y58qs45xc (4.7 JA slideshow TikTok — canonical)"
echo "[fixed] ig-integration=cmn8ycvtn02djqx0ytuisn9mw (4.7 JA slideshow Instagram — canonical)"


CAPTION=$(cat "$CAPTION_FILE")
HASHTAGS=$(cat "$HASHTAGS_FILE")
FULL_TEXT="${CAPTION} ${HASHTAGS}"

# ──────── 1. Upload all slides to Postiz CDN (CLI works fine for single uploads) ────────
echo "[1/2] Uploading 6 slides to Postiz CDN..."
declare -a SLIDE_IDS=()
declare -a SLIDE_URLS=()
for slide in "$SLIDES_DIR"/slide_*.png; do
    [ -f "$slide" ] || continue
    UPLOAD_RESP=$(postiz upload "$slide" 2>&1)
    JSON_PART=$(echo "$UPLOAD_RESP" | sed -n '/^{/,/^}/p')
    URL=$(echo "$JSON_PART" | jq -r '.path // empty' 2>/dev/null)
    ID=$(echo "$JSON_PART" | jq -r '.id // empty' 2>/dev/null)
    if [ -z "$URL" ] || [ -z "$ID" ]; then
        echo "ERR: postiz upload failed for $slide" >&2
        echo "$UPLOAD_RESP" >&2
        exit 5
    fi
    SLIDE_IDS+=("$ID")
    SLIDE_URLS+=("$URL")
    echo "  ✓ $(basename "$slide") → $URL"
    sleep 1  # rate-limit buffer like Larry's script
done

[ "${#SLIDE_URLS[@]}" -eq 0 ] && { echo "ERR: no slides uploaded" >&2; exit 6; }

# ──────── 2. Build payload + POST to /public/v1/posts (Larry pattern) ────────
echo ""
echo "[2/2] Posting to TikTok Drafts via Postiz REST API..."

# Build image[] array via jq
IDS_JSON=$(printf '%s\n' "${SLIDE_IDS[@]}"  | jq -R . | jq -s .)
URLS_JSON=$(printf '%s\n' "${SLIDE_URLS[@]}" | jq -R . | jq -s .)
IMAGES_JSON=$(jq -nc --argjson ids "$IDS_JSON" --argjson urls "$URLS_JSON" \
    '[range(0; $ids | length) | {id: $ids[.], path: $urls[.]}]')

# Article-compliant TikTok Drafts settings (matches Larry's drafts-mode):
#   content_posting_method: "UPLOAD" → pushes to TikTok app Inbox (Drafts)
#   privacy_level: "SELF_ONLY" → only visible after manual Post in app
# Plus an Instagram entry (canonical 2026-05-20) — same uploaded images,
# Postiz type:"draft" so Dais publishes from Postiz manually.
PAYLOAD=$(jq -nc \
    --arg cap "$FULL_TEXT" \
    --arg tt_int "$POSTIZ_TIKTOK_INTEGRATION_ID" \
    --arg ig_int "$POSTIZ_IG_INTEGRATION_ID" \
    --argjson images "$IMAGES_JSON" \
    '{
      type: "now",
      date: (now | todate),
      shortLink: false,
      tags: [],
      posts: [
        {
          integration: {id: $tt_int},
          value: [{content: $cap, image: $images}],
          settings: {
            __type: "tiktok",
            title: "",
            privacy_level: "SELF_ONLY",
            content_posting_method: "UPLOAD",
            duet: false,
            stitch: false,
            comment: true,
            autoAddMusic: "no",
            brand_content_toggle: false,
            brand_organic_toggle: false,
            video_made_with_ai: true
          }
        },
        {
          integration: {id: $ig_int},
          value: [{content: $cap, image: $images}],
          settings: {
            __type: "instagram-standalone",
            post_type: "post",
            collaborators: [],
            thumbnail: null
          }
        }
      ]
    }')

if [ "$DRY_RUN" = "true" ]; then
    echo "=== DRY RUN — payload ==="
    echo "$PAYLOAD" | jq '.'
    exit 0
fi

CREATE_RESP=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
    -H "Authorization: $POSTIZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo "→ Postiz response:"
echo "$CREATE_RESP" | jq '.' 2>/dev/null || echo "$CREATE_RESP"

# Extract post IDs — response is array of {postId, integration}
POST_ID=$(echo "$CREATE_RESP" | jq -r '.[0].postId // empty' 2>/dev/null)
IG_POST_ID=$(echo "$CREATE_RESP" | jq -r '.[1].postId // empty' 2>/dev/null)
if [ -z "$POST_ID" ]; then
    echo "ERR: no postId in response" >&2
    exit 7
fi

# ──────── 3. Write receipt ────────
RECEIPT="$SLIDES_DIR/../postiz-receipt.json"
jq -nc \
    --arg pid "$POST_ID" \
    --arg ig_pid "$IG_POST_ID" \
    --arg tt_int "$POSTIZ_TIKTOK_INTEGRATION_ID" \
    --arg ig_int "$POSTIZ_IG_INTEGRATION_ID" \
    --arg cap "$FULL_TEXT" \
    --argjson images "$IMAGES_JSON" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{
      postiz_post_id: $pid,
      postiz_ig_post_id: $ig_pid,
      tiktok_integration_id: $tt_int,
      instagram_integration_id: $ig_int,
      mode: "drafts",
      content_posting_method: "UPLOAD",
      privacy_level: "SELF_ONLY",
      caption: $cap,
      slide_count: ($images | length),
      images: $images,
      published_at_utc: $ts,
      next_step: "Open TikTok app → Drafts/Inbox → review → tap Post (TT); Postiz → Drafts → publish (IG)"
    }' > "$RECEIPT"

echo ""
echo "✓ TikTok Drafts ready (6 slides). Postiz post: $POST_ID"
echo "  Receipt: $RECEIPT"
echo "  Next: open TikTok app → Drafts/Inbox → tap Post."
