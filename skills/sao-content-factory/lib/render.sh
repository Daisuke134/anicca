#!/usr/bin/env bash
# lib/render.sh — Remotion render wrapper
set -euo pipefail

REMOTION_DIR="${REMOTION_DIR:-$HOME/anicca-project/sao-content-factory/remotion}"

# render_reel <composition_id> <output_mp4>
render_reel() {
  local comp_id="$1"
  local out="$2"

  [ -d "$REMOTION_DIR" ] || { echo "ERR: REMOTION_DIR not found: $REMOTION_DIR" >&2; return 3; }

  cd "$REMOTION_DIR"
  npx remotion render src/index.ts "$comp_id" "$out" \
    --jpeg-quality=90 --concurrency=4 \
    >&2 \
    || { echo "ERR: remotion render failed for $comp_id" >&2; return 4; }

  [ -f "$out" ] || { echo "ERR: render produced no output: $out" >&2; return 4; }
}

# encode_small <input_mp4> <output_mp4>
# Re-encode for smaller size (Email attachment)
encode_small() {
  local in="$1"
  local out="$2"
  ffmpeg -y -loglevel error -i "$in" \
    -c:v libx264 -preset slow -crf 24 \
    -c:a aac -b:a 128k \
    -movflags +faststart \
    "$out"
}

# install_assets <entity_dir>
# Copies entity assets (img/, broll/, vo/, bgm/) into Remotion public/
install_assets() {
  local entity_dir="$1"
  local pub="$REMOTION_DIR/public"
  mkdir -p "$pub/img" "$pub/broll" "$pub/vo" "$pub/bgm"

  # Clear existing per-render
  rm -f "$pub/img"/* "$pub/broll"/* "$pub/vo"/* "$pub/bgm"/*

  [ -d "$entity_dir/img" ] && cp -f "$entity_dir/img/"* "$pub/img/" 2>/dev/null || true
  [ -d "$entity_dir/broll" ] && cp -f "$entity_dir/broll/"* "$pub/broll/" 2>/dev/null || true
  [ -d "$entity_dir/vo" ] && cp -f "$entity_dir/vo/"* "$pub/vo/" 2>/dev/null || true
  [ -d "$entity_dir/bgm" ] && cp -f "$entity_dir/bgm/"* "$pub/bgm/" 2>/dev/null || true
}

# generate_data_ts <entity_json> <output_ts_file>
# Converts entity.json scenes → src/data/<entity>.ts (TS module)
# For now we just symlink/regenerate src/data/andon.ts based on entity JSON
# A future version will template multiple entities
generate_data_ts() {
  local entity_json="$1"
  local out="$2"
  # Read scenes from entity JSON, emit a TS module
  jq -r '
    "import type { Scene } from \"./types\";\n\nexport const scenes: Scene[] = " +
    (.scenes | tostring) +
    " as Scene[];"
  ' "$entity_json" > "$out"
}
