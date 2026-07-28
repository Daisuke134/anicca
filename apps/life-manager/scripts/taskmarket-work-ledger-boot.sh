#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LIFE_MANAGER_ENV_FILE:-${HOME}/.openclaw/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

export TASKMARKET_WORKER_ADDRESS="${TASKMARKET_WORKER_ADDRESS:-0xd7Db94062AFec8a86F70250B931C77619acf8937}"
export TASKMARKET_SELF_WALLETS_MODULE="${TASKMARKET_SELF_WALLETS_MODULE:-${HOME}/anicca/skills/earn/x402-sell/lib/self-wallets.mjs}"

exec /opt/homebrew/bin/timeout 240 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/record-taskmarket-work.js" \
  --worker "$TASKMARKET_WORKER_ADDRESS" \
  --task "0x37f67e062d4384c3adf252844545e916128c377569ac418ae46c7cc1a2a97c7d"
