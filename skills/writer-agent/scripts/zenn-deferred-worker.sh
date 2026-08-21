#!/usr/bin/env bash
# One-shot launchd entrypoint. The Python worker scans the durable run-dir queue and exits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a
ARTICLE_ROOT="${ARTICLE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
STATE_DIR="${ARTICLE_STATE_DIR:-$ARTICLE_ROOT/state}"
PUBLICATION_PAUSE_FILE="${ARTICLE_PUBLICATION_PAUSE_FILE:-$STATE_DIR/.publication-paused}"
if [ -f "$PUBLICATION_PAUSE_FILE" ]; then
  echo "zenn-deferred-worker: publication paused file=$PUBLICATION_PAUSE_FILE"
  exit 0
fi
SYSTEM_PYTHON="${WRITER_SYSTEM_PYTHON:-/opt/homebrew/bin/python3}"
if [ ! -x "$SYSTEM_PYTHON" ]; then
  echo "Zenn worker system Python is unavailable: $SYSTEM_PYTHON" >&2
  exit 75
fi
exec "$SYSTEM_PYTHON" "$SCRIPT_DIR/zenn-deferred-worker.py" "$@"
