#!/usr/bin/env bash
set -euo pipefail
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/life-manager}"
LM_CONNECTOR_ENV_FILE="${LM_CONNECTOR_ENV_FILE:-$LIFE_MANAGER_STATE_HOME/.env}"
set -a
[ ! -f "$LM_CONNECTOR_ENV_FILE" ] || . "$LM_CONNECTOR_ENV_FILE"
set +a
exec node "$LIFE_MANAGER_REPO/apps/life-manager/lib/outbound-guardian.js"
