#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
set -a
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=gig_paths.sh
source "$SCRIPT_DIR/gig_paths.sh"
. "$GIG_ENV_FILE"
set +a
exec /opt/homebrew/bin/openclaw webhooks gmail run
