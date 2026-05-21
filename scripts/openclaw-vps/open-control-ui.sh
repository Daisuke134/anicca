#!/usr/bin/env bash
# Control UI を開く。その前に sessionFile を相対パスに正規化する（gateway が絶対パスで上書きするため都度必要）。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
node "$SCRIPT_DIR/local-fix-session-path.js"
open "http://127.0.0.1:18789/chat?session=agent%3Aanicca%3Amain"
