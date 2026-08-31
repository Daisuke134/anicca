#!/usr/bin/env bash
set -euo pipefail
MR_BOT_REPO="${MR_BOT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$MR_BOT_REPO" ] || { echo "MR_BOT_REPO could not be resolved" >&2; exit 2; }
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
MR_BOT_STATE_HOME="${MR_BOT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot}"
LM_CONNECTOR_ENV_FILE="${LM_CONNECTOR_ENV_FILE:-$MR_BOT_STATE_HOME/.env}"
set -a
[ ! -f "$LM_CONNECTOR_ENV_FILE" ] || . "$LM_CONNECTOR_ENV_FILE"
set +a
exec node "$MR_BOT_REPO/apps/mr-bot/lib/outbound-guardian.js"
