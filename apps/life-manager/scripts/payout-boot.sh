#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LIFE_MANAGER_ENV_FILE:-${HOME}/.local/state/life-manager/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

export AGENT_WALLET_ADDRESS="${AGENT_WALLET_ADDRESS:-0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad}"
export LM_AGENT_WALLET_PATH="${LM_AGENT_WALLET_PATH:-${HOME}/.cloak/life-manager-agent-wallet.json}"
export LM_PAYOUT_RESERVE_USDC_ATOMIC="${LM_PAYOUT_RESERVE_USDC_ATOMIC:-35000000}"
export LM_PAYOUT_FACILITATOR_URL="${LM_PAYOUT_FACILITATOR_URL:-http://127.0.0.1:8406}"
export LM_PAYOUT_FACILITATOR_START="${LM_PAYOUT_FACILITATOR_START:-${HOME}/anicca-oss/services/facilitator/start.sh}"

exec /opt/homebrew/bin/timeout 240 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/run-agent-payout.js" "$@"
