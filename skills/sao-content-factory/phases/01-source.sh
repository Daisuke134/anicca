#!/usr/bin/env bash
# 01-source.sh — fetch blog + images + YouTube
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/sao-content-factory}"
source "$SKILL_DIR/lib/source.sh"

[ -n "${ENTITY_JSON:-}" ] && [ -n "${VERSION_DIR:-}" ] || { echo "ENTITY_JSON / VERSION_DIR not set" >&2; exit 2; }

BLOG_URL=$(jq -r '.source_blog // empty' "$ENTITY_JSON")
YT_URL=$(jq -r '.source_youtube // empty' "$ENTITY_JSON")

# 1. Blog scrape
if [ -n "$BLOG_URL" ] && [ "$BLOG_URL" != "null" ]; then
  scrape_blog "$BLOG_URL" "$VERSION_DIR/docs/source.md"

  # 2. Image download (extract URLs from blog markdown)
  while IFS= read -r url; do
    [ -z "$url" ] && continue
    fname=$(basename "${url%%\?*}")
    download_image "$url" "$VERSION_DIR/img/$fname" || echo "  warn: failed to download $url" >&2
  done < <(extract_image_urls "$VERSION_DIR/docs/source.md")
fi

# 3. YouTube download
if [ -n "$YT_URL" ] && [ "$YT_URL" != "null" ]; then
  download_youtube "$YT_URL" "$VERSION_DIR/broll" "yt_full"
fi

echo "phase 01 ok"
