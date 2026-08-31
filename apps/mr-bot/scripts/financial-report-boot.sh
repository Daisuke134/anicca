#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec /opt/homebrew/bin/timeout 240 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/../lib/report-job-adapter.js" enqueue "$@"
