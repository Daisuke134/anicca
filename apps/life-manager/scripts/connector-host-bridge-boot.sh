#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${LM_CONNECTOR_ENV_FILE:-${HOME}/.openclaw/.env}"
TOKEN_FILE="${LM_CONNECTOR_BRIDGE_TOKEN_FILE:-${HOME}/.local/state/life-manager/connector-host-bridge/token}"

if [[ ! -f "$ENV_FILE" || ! -f "$TOKEN_FILE" ]]; then
  echo "Connector host bridge unavailable" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

LM_CONNECTOR_BRIDGE_TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
export LM_CONNECTOR_BRIDGE_TOKEN
export LM_CONNECTOR_BRIDGE_HOST="127.0.0.1"
export LM_CONNECTOR_BRIDGE_PORT="${LM_CONNECTOR_BRIDGE_PORT:-18793}"

exec /opt/homebrew/bin/node "$APP_DIR/scripts/connector-host-bridge-server.js"
