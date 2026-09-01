#!/bin/bash
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/store-recordings.py"
