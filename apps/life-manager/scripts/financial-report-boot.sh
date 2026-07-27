#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${HOME}/.openclaw/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

export LM_FINANCIAL_REPORT_RESERVE_USDC_ATOMIC="${LM_FINANCIAL_REPORT_RESERVE_USDC_ATOMIC:-35000000}"

exec /opt/homebrew/bin/timeout 240 /opt/homebrew/bin/node \
  "$SCRIPT_DIR/run-financial-reports.js" "$@"
