#!/usr/bin/env bash
# Reuse the canonical shared instagrapi poster; this file only pins its interpreter and path.
set -euo pipefail

if [ -n "${INSTAGRAPI_PYTHON:-}" ]; then
  PYTHON="$INSTAGRAPI_PYTHON"
elif [ -x "$HOME/.cache/instagrapi-venv/bin/python" ]; then
  PYTHON="$HOME/.cache/instagrapi-venv/bin/python"
else
  PYTHON="$(command -v python3 || true)"
fi
POSTER="${LM_INSTAGRAM_POSTER:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/earn/marketing-engine/poster.py}"

if [ ! -x "$PYTHON" ] || [ ! -f "$POSTER" ]; then
  printf '{"outcome":"failed","post_url":null,"error":"instagram adapter unavailable"}\n'
  exit 69
fi

exec "$PYTHON" "$POSTER" "$@"
