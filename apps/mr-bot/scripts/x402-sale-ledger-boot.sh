#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${MR_BOT_ENV_FILE:-${HOME}/.local/state/mr-bot/.env}"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/load-env-file.sh"
lm_load_env_file "$ENV_FILE"

export X402_SELL_STATE_DIR="${X402_SELL_STATE_DIR:-${HOME}/anicca/skills/earn/x402-sell/state}"
export X402_SELF_WALLETS_MODULE="${X402_SELF_WALLETS_MODULE:-${HOME}/anicca/skills/earn/x402-sell/lib/self-wallets.mjs}"

exec /opt/homebrew/bin/timeout 240 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/record-x402-sales.js" \
  --state-dir "$X402_SELL_STATE_DIR"
