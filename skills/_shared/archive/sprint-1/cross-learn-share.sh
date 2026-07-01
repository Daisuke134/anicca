#!/usr/bin/env bash
# cross-learn-share.sh — REQ-D2 SHARE: publish novel lesson + claim-check dedup.
# SECURITY: params via ENV VAR, no heredoc interpolation. FIND-2-001 fix.
#
# Usage: cross-learn-share.sh <slot> <requestId> <outcome> <body-file>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_REQ_ID="${2:-}"
export ANICCA_OUTCOME="${3:-}"
export ANICCA_BODY_FILE="${4:-/dev/null}"
export ANICCA_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$ANICCA_SHARED_DIR/cross-learn-share-dispatch.py"
