#!/usr/bin/env bash
# migrate-legacy-state.sh — copy legacy Life Manager state into the portable
# data root. COPY ONLY: the legacy loop remains the owner of its store until the
# Order 14 cutover, so this script never moves, deletes, or rewrites a source
# file, and never overwrites a destination file the new loop already owns.
#
#   source : $LM_LEGACY_STATE_ROOT (default: $HOME/.openclaw/state)
#            -> {lm-video, life-manager-dev}
#   dest   : ${LM_DATA_DIR:-$HOME/.local/state/life-manager}/state/
#
# Idempotent: re-running skips files that already exist at the destination.
# Every run verifies, by readback, that each migrated file's byte size at the
# destination is at least the legacy source's size (append-only ledgers may
# legitimately grow at the destination; they may never be smaller).
set -euo pipefail

LEGACY_STATE_ROOT="${LM_LEGACY_STATE_ROOT:-$HOME/.openclaw/state}"
DATA_ROOT="${LM_DATA_DIR:-$HOME/.local/state/life-manager}"
DEST_ROOT="$DATA_ROOT/state"

file_size() {
  # macOS (BSD stat) first, GNU stat fallback.
  stat -f%z "$1" 2>/dev/null || stat -c%s "$1"
}

total_copied=0
total_skipped=0
total_verified=0

for name in lm-video life-manager-dev; do
  src="$LEGACY_STATE_ROOT/$name"
  dst="$DEST_ROOT/$name"
  if [ ! -d "$src" ]; then
    printf 'skip %s: no legacy dir at %s\n' "$name" "$src"
    continue
  fi
  mkdir -p "$dst"
  copied=0
  skipped=0
  while IFS= read -r -d '' source_file; do
    relative="${source_file#"$src"/}"
    target="$dst/$relative"
    if [ -e "$target" ]; then
      skipped=$((skipped + 1))
    else
      mkdir -p "$(dirname "$target")"
      cp -p "$source_file" "$target"
      copied=$((copied + 1))
    fi
    # Readback verification for every legacy file, copied or pre-existing.
    src_size="$(file_size "$source_file")"
    dst_size="$(file_size "$target")"
    if [ "$dst_size" -lt "$src_size" ]; then
      printf 'size mismatch after copy: %s (%s bytes) vs %s (%s bytes)\n' \
        "$target" "$dst_size" "$source_file" "$src_size" >&2
      exit 1
    fi
    total_verified=$((total_verified + 1))
  done < <(find "$src" -type f -print0)
  printf '%s: copied %s file(s), skipped %s existing file(s) -> %s\n' \
    "$name" "$copied" "$skipped" "$dst"
  total_copied=$((total_copied + copied))
  total_skipped=$((total_skipped + skipped))
done

printf 'done: %s copied, %s skipped, %s verified by size readback; legacy store untouched at %s\n' \
  "$total_copied" "$total_skipped" "$total_verified" "$LEGACY_STATE_ROOT"
