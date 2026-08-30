#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LIFE_MANAGER_MARKETING_ENV_FILE:-${HOME}/.local/state/life-manager/private/marketing.env}"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/load-env-file.sh"
lm_load_env_file "$ENV_FILE"
exec /opt/homebrew/bin/timeout 1200 /opt/homebrew/bin/node "$SCRIPT_DIR/honne-ja-cycle.js" run-anicca-jp4
