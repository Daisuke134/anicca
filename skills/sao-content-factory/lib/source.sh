#!/usr/bin/env bash
# lib/source.sh — wrappers for source ingestion
set -euo pipefail

# scrape_blog <url> <output_md>
scrape_blog() {
  local url="$1"
  local out="$2"
  /opt/homebrew/bin/firecrawl scrape "$url" markdown > "$out"
  [ -s "$out" ] || { echo "ERR: firecrawl returned empty for $url" >&2; return 4; }
}

# download_image <url> <output_path>
# Skips if file already exists (idempotent)
download_image() {
  local url="$1"
  local out="$2"
  [ -f "$out" ] && return 0
  curl -fsSL --connect-timeout 20 --retry 3 -o "$out" "$url" \
    || { echo "ERR: curl failed for $url" >&2; return 4; }
}

# download_youtube <url> <output_dir> <output_basename>
# Skips if .mp4 already exists
download_youtube() {
  local url="$1"
  local dir="$2"
  local base="$3"
  local out="$dir/${base}.mp4"
  [ -f "$out" ] && return 0
  cd "$dir"
  /opt/homebrew/bin/yt-dlp \
    -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
    --merge-output-format mp4 \
    -o "${base}.%(ext)s" \
    "$url" >&2
  [ -f "$out" ] || { echo "ERR: yt-dlp produced no output" >&2; return 4; }
}

# extract_image_urls <markdown_file>
# Prints all image URLs found in markdown (one per line)
extract_image_urls() {
  local md="$1"
  grep -oE '!\[[^]]*\]\(https?://[^)]+\)' "$md" | sed -E 's|!\[[^]]*\]\(([^)]+)\)|\1|'
}
