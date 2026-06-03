#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# runtime/memu/setup.sh — idempotent dependency check for spec-11 memU stack.
#
# Verifies: python3.13 venv, memu-py install, Ollama daemon, nomic-embed-text model,
# DEEPSEEK_API_KEY in env. Creates venv if missing. Pulls embedding model if missing.

set -euo pipefail

VENV="${MEMU_VENV:-$HOME/.anicca-genesis/memU-test/.venv}"
ENV_FILE="$HOME/.openclaw/.env"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"

green() { printf '\033[32m✓\033[0m %s\n' "$1"; }
red()   { printf '\033[31m✗\033[0m %s\n' "$1"; exit 1; }

# 1. python3.13
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  red "$PYTHON_BIN not found; install via 'brew install python@3.13' or uv"
fi
green "python3.13 at $(command -v $PYTHON_BIN)"

# 2. venv
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "creating venv at $VENV"
  mkdir -p "$(dirname "$VENV")"
  "$PYTHON_BIN" -m venv "$VENV"
fi
green "venv ready at $VENV"

# 3. memu-py
if ! "$VENV/bin/pip" show memu-py >/dev/null 2>&1; then
  echo "installing memu-py..."
  "$VENV/bin/pip" install --quiet 'memu-py>=1.5,<2.0'
fi
green "memu-py $($VENV/bin/pip show memu-py | awk '/Version:/{print $2}')"

# 4. ollama
if ! command -v ollama >/dev/null 2>&1; then
  red "ollama not found; install via 'brew install ollama'"
fi
green "ollama at $(command -v ollama)"

# 5. embedding model
if ! ollama list 2>/dev/null | grep -q '^nomic-embed-text'; then
  echo "pulling nomic-embed-text..."
  ollama pull nomic-embed-text
fi
green "nomic-embed-text pulled"

# 6. env var
if [[ -f "$ENV_FILE" ]]; then
  set -a; . "$ENV_FILE"; set +a
fi
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  red "DEEPSEEK_API_KEY missing from env (expected in $ENV_FILE)"
fi
green "DEEPSEEK_API_KEY present (len=${#DEEPSEEK_API_KEY})"

# 7. ollama reachable (quick probe)
if ! curl -fsS --max-time 3 http://localhost:11434/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"nomic-embed-text","input":"ping"}' >/dev/null 2>&1; then
  red "ollama /v1/embeddings unreachable on localhost:11434 (is the daemon running?)"
fi
green "ollama /v1/embeddings responding"

echo
echo "spec 11 setup OK — run \`bash runtime/memu/wrappers/heartbeat.py retrieve\` to smoke-test"
