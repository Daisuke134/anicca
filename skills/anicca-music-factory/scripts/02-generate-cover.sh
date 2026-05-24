#!/usr/bin/env bash
# Generate one cover via FAL FLUX 1.1
#
# Usage: 02-generate-cover.sh <prompt> <output_dir>
# Outputs: $output_dir/cover.jpg (1024x1024)

set -euo pipefail

PROMPT="$1"
OUTDIR="$2"

[ -z "${FAL_KEY:-}" ] && { echo "ERR: FAL_KEY not set" >&2; exit 3; }

mkdir -p "$OUTDIR"

PAYLOAD=$(jq -nc --arg p "$PROMPT" '{prompt:$p, image_size:"square_hd", num_images:1, output_format:"jpeg"}')

RESP=$(curl -sS -X POST "https://fal.run/fal-ai/flux-pro/v1.1" \
  -H "Authorization: Key $FAL_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

URL=$(echo "$RESP" | jq -r '.images[0].url // empty')
if [ -z "$URL" ]; then
  echo "ERR: FAL no image url" >&2
  echo "$RESP" >&2
  exit 4
fi

curl -sS -L "$URL" -o "$OUTDIR/cover.jpg"
echo "$RESP" > "$OUTDIR/.fal-cover.json"
echo "$URL" > "$OUTDIR/.fal-cover-url.txt"
SIZE=$(sips -g pixelWidth -g pixelHeight "$OUTDIR/cover.jpg" 2>/dev/null | grep pixel | awk '{print $2}' | paste -sd 'x' -)
echo "OK cover.jpg ${SIZE}"
