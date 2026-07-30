#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON3="${PYTHON3:-$(command -v python3)}"
exec "$PYTHON3" "$HERE/scripts/install_local.py" "$@"
