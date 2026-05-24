#!/usr/bin/env bash
# Step 1 of article: Find Hooks From TikTok.
# Uses Apify clockworks/tiktok-scraper to fetch top videos in target hashtags.
# Extracts the post text (caption + first text overlay = the hook).
#
# Usage: 01-discover-tiktok-hooks.sh <output_dir>
# Output: $output_dir/tiktok-hooks.json (top viral posts in niche)

set -euo pipefail

OUTDIR="$1"
mkdir -p "$OUTDIR"

[ -z "${APIFY_API_TOKEN:-}" ] && { echo "ERR: APIFY_API_TOKEN not set" >&2; exit 3; }

# Niche hashtags for Anicca iOS (日本語: マインドフルネス/瞑想/仏教)
HASHTAGS_JSON='["マインドフルネス","瞑想","仏教","禅","自己肯定感","メンタルケア","不安","人生"]'

echo "→ Apify TikTok scraper: hashtags=$HASHTAGS_JSON"

PAYLOAD=$(jq -nc --argjson tags "$HASHTAGS_JSON" '{
  hashtags: $tags,
  resultsPerPage: 10,
  shouldDownloadVideos: false,
  shouldDownloadCovers: false,
  shouldDownloadSubtitles: false,
  shouldDownloadSlideshowImages: true,
  proxyCountryCode: "None"
}')

# clockworks/tiktok-scraper, run-sync, return dataset items
RESP=$(curl -sS -X POST \
    "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token=${APIFY_API_TOKEN}&timeout=120" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

# Validate response
if ! echo "$RESP" | jq -e 'type == "array"' > /dev/null 2>&1; then
    echo "ERR: Apify response not an array:" >&2
    echo "$RESP" | head -c 500 >&2
    exit 4
fi

COUNT=$(echo "$RESP" | jq 'length')
echo "→ retrieved $COUNT TikTok posts"

# Save raw + extract hooks (text + viewCount + diggCount + hashtags + slideshow images)
echo "$RESP" > "$OUTDIR/.tiktok-raw.json"
echo "$RESP" | jq '[
  .[]
  | {
      text: (.text // ""),
      author: (.authorMeta.name // ""),
      playCount: (.playCount // 0),
      diggCount: (.diggCount // 0),
      shareCount: (.shareCount // 0),
      commentCount: (.commentCount // 0),
      isSlideshow: ((.imagePost // null) != null),
      slideshow_image_urls: ([.imagePost.images[]?.imageURL.urlList[0] // empty]),
      hashtags: ([.hashtags[]?.name // empty]),
      url: (.webVideoUrl // "")
    }
  | select(.playCount > 5000)
] | sort_by(-.playCount) | .[0:20]' > "$OUTDIR/tiktok-hooks.json"

# Download top 3 viral slideshow first-image URLs for Claude vision in step 2
mkdir -p "$OUTDIR/viral-slideshows"
jq -r '
  [.[] | select(.isSlideshow == true and (.slideshow_image_urls | length) > 0)]
  | .[0:5]
  | .[]
  | .slideshow_image_urls[0]
' "$OUTDIR/tiktok-hooks.json" | while read -r url; do
    [ -z "$url" ] && continue
    fname=$(echo "$url" | md5 -q 2>/dev/null || echo "$url" | md5sum | awk '{print $1}')
    out="$OUTDIR/viral-slideshows/${fname}.jpg"
    if curl -sSL --max-time 15 "$url" -o "$out"; then
        size=$(stat -f "%z" "$out" 2>/dev/null || stat -c "%s" "$out" 2>/dev/null)
        if [ "${size:-0}" -lt 5000 ]; then
            rm -f "$out"
        fi
    fi
done
shopt -s nullglob
SLIDES=("$OUTDIR/viral-slideshows/"*.jpg)
SLIDE_COUNT=${#SLIDES[@]}
echo "→ $SLIDE_COUNT viral slideshow first-images saved (for Claude vision)"

TOP_COUNT=$(jq 'length' "$OUTDIR/tiktok-hooks.json")
echo "OK $TOP_COUNT viral hooks saved → $OUTDIR/tiktok-hooks.json"
echo ""
echo "Top 3 hooks (by view count):"
jq -r '.[0:3] | .[] | "  • [\(.playCount) views] \(.text[0:80])"' "$OUTDIR/tiktok-hooks.json"
