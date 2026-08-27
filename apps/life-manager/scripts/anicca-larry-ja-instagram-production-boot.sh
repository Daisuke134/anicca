#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV_FILE="${LIFE_MANAGER_MARKETING_ENV_FILE:-$HOME/.local/state/life-manager/private/marketing.env}"
set -a; source "$ENV_FILE"; set +a
exec /opt/homebrew/bin/timeout 1200 /opt/homebrew/bin/node "$SCRIPT_DIR/anicca-larry-ja-canary.js" run-ja-larry-production
