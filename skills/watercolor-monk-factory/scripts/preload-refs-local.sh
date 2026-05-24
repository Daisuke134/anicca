#!/usr/bin/env bash
# One-time bootstrap: download 13 cached fal flux ref URLs to local jpg files.
# After this runs once, generate.sh's Ken Burns step reads jpgs directly (no network).
# Idempotent: skips if local file already exists and is non-empty.
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
STATE="$ROOT/state"

DOWNLOADED=0
SKIPPED=0
FAILED=0
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13; do
  URL_FILE="$STATE/jp_url_$i.txt"
  REF_FILE="$STATE/jp_ref_$i.jpg"
  if [ ! -f "$URL_FILE" ]; then
    echo "  ⚠ missing $URL_FILE — skip"; FAILED=$((FAILED+1)); continue
  fi
  if [ -f "$REF_FILE" ] && [ -s "$REF_FILE" ]; then
    SIZE=$(du -h "$REF_FILE" | cut -f1)
    echo "  ✓ $i already local ($SIZE)"
    SKIPPED=$((SKIPPED+1)); continue
  fi
  URL=$(cat "$URL_FILE")
  echo "  ↓ scene $i: ${URL:0:60}..."
  curl -sS -L -o "$REF_FILE" "$URL"
  if [ -s "$REF_FILE" ]; then
    SIZE=$(du -h "$REF_FILE" | cut -f1)
    echo "    ✅ $REF_FILE ($SIZE)"
    DOWNLOADED=$((DOWNLOADED+1))
  else
    echo "    ❌ download failed"
    FAILED=$((FAILED+1))
  fi
done

echo ""
echo "  summary: $DOWNLOADED newly downloaded, $SKIPPED already local, $FAILED failed"
echo "  → state/jp_ref_NN.jpg ready for ffmpeg Ken Burns"
