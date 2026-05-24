#!/usr/bin/env bash
# quarto-render.sh — render a homework qmd to PDF using the user's naist-thesis template.
# Usage: bash scripts/quarto-render.sh <input.qmd> <output.pdf>
# DRY_RUN=true to skip the actual quarto invocation.
set -euo pipefail

IN="${1:?input qmd required}"
OUT="${2:?output pdf path required}"
DRY_RUN="${DRY_RUN:-false}"

if [ ! -f "$IN" ]; then
  echo "quarto-render: input qmd not found: $IN" >&2
  exit 66
fi

mkdir -p "$(dirname "$OUT")"

if [ "$DRY_RUN" = "true" ]; then
  echo "[DRY_RUN] would: quarto render $IN --to pdf -o $OUT"
  exit 0
fi

if ! command -v quarto >/dev/null 2>&1; then
  echo "quarto-render: quarto not installed on host. brew install --cask quarto" >&2
  exit 127
fi

# Quarto needs --output to be just a filename relative to the input dir; we move after.
TMPDIR="$(mktemp -d)"
cp "$IN" "$TMPDIR/input.qmd"
( cd "$TMPDIR" && quarto render input.qmd --to pdf )
mv "$TMPDIR/input.pdf" "$OUT"
rm -rf "$TMPDIR"
echo "quarto-render: wrote $OUT"
