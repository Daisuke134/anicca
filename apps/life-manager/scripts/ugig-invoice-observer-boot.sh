#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LIFE_MANAGER_ENV_FILE:-${HOME}/.openclaw/.env}"
UGIG_API_KEY_FILE="${UGIG_API_KEY_FILE:-${HOME}/.config/life-manager/credentials/ugig-api-key}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ ! -r "$UGIG_API_KEY_FILE" ]]; then
  echo "UGIG_API_KEY_FILE is not readable" >&2
  exit 1
fi

export UGIG_API_KEY
UGIG_API_KEY="$(tr -d '\r\n' < "$UGIG_API_KEY_FILE")"
export UGIG_DELIVERIES_CONFIG="${UGIG_DELIVERIES_CONFIG:-${SCRIPT_DIR}/ugig-deliveries.json}"

/opt/homebrew/bin/timeout 180 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/observe-ugig-work.js"
