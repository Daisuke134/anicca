#!/usr/bin/env bash
# Step 3 of article: Pick Images From Pinterest.
# 1. Use playwright-cli to render Pinterest search results (JS-required)
# 2. Extract pin URLs from rendered DOM
# 3. For each pin URL, curl pin page → parse i.pinimg.com URL from HTML
# 4. Download top 6 images at 1200x resolution
#
# Usage: 03-pinterest-download.sh <analysis_json> <output_dir>
# Output: $output_dir/image_01.jpg .. image_06.jpg

set -uo pipefail

ANALYSIS="$1"
OUTDIR="$2"
mkdir -p "$OUTDIR"

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# Pull queries from analysis (top 3 to keep it fast)
QUERIES=()
while IFS= read -r line; do QUERIES+=("$line"); done < <(jq -r '.pinterest_queries[]' "$ANALYSIS" | head -3)

echo "→ Pinterest queries: ${QUERIES[*]}"

# Use a unique session name per run to avoid collisions
SESSION="pin-$(date +%s)"

declare -a PIN_URLS=()
for q in "${QUERIES[@]}"; do
    enc=$(printf '%s' "$q" | jq -sRr '@uri')
    echo "→ rendering Pinterest search: '$q'"
    playwright-cli -s="$SESSION" open "https://www.pinterest.com/search/pins/?q=$enc" >/dev/null 2>&1
    sleep 6  # let JS load pins

    # Extract pin URLs from snapshot (matches /pin/<digits>/)
    while IFS= read -r url; do
        [ -z "$url" ] && continue
        full="https://www.pinterest.com$url"
        # Dedupe + cap
        if [[ ! " ${PIN_URLS[*]:-} " =~ " $full " ]]; then
            PIN_URLS+=("$full")
        fi
        [ "${#PIN_URLS[@]}" -ge 12 ] && break  # gather extras for fallback
    done < <(playwright-cli -s="$SESSION" snapshot 2>/dev/null | grep -oE '/pin/[0-9]+/' | sort -u | head -8)

    [ "${#PIN_URLS[@]}" -ge 12 ] && break
done

playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true

if [ "${#PIN_URLS[@]}" -lt 1 ]; then
    echo "ERR: no pin URLs scraped from Pinterest search" >&2
    exit 4
fi

echo "→ found ${#PIN_URLS[@]} pin URLs, fetching + filtering images..."

# Article filters (Step 3):
#  - Ratio: 9:16 portrait priority (0.5 ≤ w/h ≤ 0.65)
#  - Bold high-contrast: skip low-saturation/pastel images
#  - Allow landscape as fallback ("script will crop it")

filter_image() {
    # Returns 0 if image passes filter, 1 if rejected. Args: file_path
    local f="$1"
    # 1. Dimensions check via sips
    local dims wh
    dims=$(sips -g pixelWidth -g pixelHeight "$f" 2>/dev/null | awk '/pixelWidth/{w=$2} /pixelHeight/{h=$2} END{print w" "h}')
    local w=${dims%% *}
    local h=${dims##* }
    [ -z "$w" ] || [ -z "$h" ] || [ "$w" -lt 600 ] || [ "$h" -lt 600 ] && return 1

    # 2. Aspect ratio: prefer portrait. Skip extreme landscape (w/h > 1.8)
    # bash float math via awk
    local ratio_ok
    ratio_ok=$(awk -v w="$w" -v h="$h" 'BEGIN{r=w/h; if(r<=1.8) print "ok"; else print "no"}')
    [ "$ratio_ok" != "ok" ] && return 1

    # 3. Saturation/contrast check via sips (cheap proxy: file size after JPEG q70)
    # Skip if extremely low contrast / pastel (re-encoded size very small relative to dims)
    local pixels=$((w * h))
    local fsize
    fsize=$(stat -f "%z" "$f" 2>/dev/null || stat -c "%s" "$f" 2>/dev/null)
    local bytes_per_pixel
    bytes_per_pixel=$(awk -v s="$fsize" -v p="$pixels" 'BEGIN{print s/p}')
    # Heuristic: pastels & flat images compress very well (low bpp). Reject < 0.05.
    local contrast_ok
    contrast_ok=$(awk -v bpp="$bytes_per_pixel" 'BEGIN{if(bpp>=0.05) print "ok"; else print "no"}')
    [ "$contrast_ok" != "ok" ] && return 1

    return 0
}

# Download up to 6 (with filtering)
i=1
ATTEMPTED=0
for pin_url in "${PIN_URLS[@]}"; do
    [ "$i" -gt 6 ] && break
    ATTEMPTED=$((ATTEMPTED + 1))

    HTML=$(curl -sSL --max-time 15 -A "$UA" "$pin_url" 2>/dev/null)
    IMG_URL=$(echo "$HTML" | grep -oE 'https://i\.pinimg\.com/(originals|1200x|736x)/[^"]+\.(jpg|png|webp)' | sort -u | head -1)

    if [ -z "$IMG_URL" ]; then
        echo "  ! no image URL in pin: $pin_url"
        continue
    fi

    tmp="$OUTDIR/.tmp_image.jpg"
    if curl -sSL --max-time 30 -A "$UA" "$IMG_URL" -o "$tmp" 2>/dev/null; then
        if filter_image "$tmp"; then
            out="$OUTDIR/image_$(printf '%02d' "$i").jpg"
            mv "$tmp" "$out"
            size=$(stat -f "%z" "$out" 2>/dev/null || stat -c "%s" "$out" 2>/dev/null)
            dims=$(sips -g pixelWidth -g pixelHeight "$out" 2>/dev/null | awk '/pixelWidth/{w=$2} /pixelHeight/{h=$2} END{print w"x"h}')
            echo "  ✓ image_$(printf '%02d' "$i").jpg ($((size/1024))KB, $dims)"
            i=$((i+1))
        else
            rm -f "$tmp"
            echo "  ⊘ filter rejected: $IMG_URL"
        fi
    fi
done
rm -f "$OUTDIR/.tmp_image.jpg"

DOWNLOADED=$((i-1))
echo "→ filter pass rate: $DOWNLOADED / $ATTEMPTED attempts"

# Fallback: if filter was too strict and we have <3 images, retry without filter
if [ "$DOWNLOADED" -lt 3 ]; then
    echo "  ! too few images passed filter, retrying without filter..."
    for pin_url in "${PIN_URLS[@]}"; do
        [ "$i" -gt 6 ] && break
        out="$OUTDIR/image_$(printf '%02d' "$i").jpg"
        [ -f "$out" ] && continue

        HTML=$(curl -sSL --max-time 15 -A "$UA" "$pin_url" 2>/dev/null)
        IMG_URL=$(echo "$HTML" | grep -oE 'https://i\.pinimg\.com/(originals|1200x|736x)/[^"]+\.(jpg|png|webp)' | sort -u | head -1)
        [ -z "$IMG_URL" ] && continue

        if curl -sSL --max-time 30 -A "$UA" "$IMG_URL" -o "$out"; then
            size=$(stat -f "%z" "$out" 2>/dev/null)
            if [ "${size:-0}" -lt 5000 ]; then
                rm -f "$out"
                continue
            fi
            echo "  ✓ image_$(printf '%02d' "$i").jpg (fallback, $((size/1024))KB)"
            i=$((i+1))
        fi
    done
    DOWNLOADED=$((i-1))
fi

if [ "$DOWNLOADED" -lt 1 ]; then
    echo "ERR: 0 images downloaded" >&2
    exit 5
fi

echo "OK $DOWNLOADED Pinterest images → $OUTDIR/"
