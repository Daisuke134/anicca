#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${MR_BOT_ENV_FILE:-${HOME}/.local/state/mr-bot/.env}"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/load-env-file.sh"
lm_load_env_file "$ENV_FILE"
exec /opt/homebrew/bin/timeout 300 /opt/homebrew/bin/node "$SCRIPT_DIR/instagram-metrics-due.js"
