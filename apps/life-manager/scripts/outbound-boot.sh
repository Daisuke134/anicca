#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec /opt/homebrew/bin/timeout 900 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/outbound-pass.js" "$@"
