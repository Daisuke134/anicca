#!/usr/bin/env bash
# run.sh — bootstrap venv + start LiveKit Anicca Realtime agent
# Usage: run.sh [dev|connect|start]
#   dev     interactive local dev (LiveKit Cloud sandbox, hot reload)
#   start   production worker (long-running)
#   connect connect once to a specific room (debug)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$SKILL_DIR/.venv"
MODE="${1:-dev}"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

if [ ! -d "$VENV" ]; then
  echo "▶ creating venv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip wheel
  "$VENV/bin/pip" install -r "$SKILL_DIR/requirements.txt"
  "$VENV/bin/python" -m livekit.agents.cli download-files || true
fi

cd "$SKILL_DIR"
exec "$VENV/bin/python" main.py "$MODE"
