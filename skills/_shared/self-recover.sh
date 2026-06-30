#!/usr/bin/env bash
# self-recover.sh — REQ-F1 dispatcher (NO HUMAN, v7).
# Routes (slot, reason, evidence) → Group J handlers via lib/group_j.py.
#
# SECURITY: untrusted evidence is passed via ENV VAR (not heredoc) to prevent
# shell→Python injection. FIND-2-001 fix.
#
# Usage: self-recover.sh <slot> <reason> <evidence>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_REASON="${2:-unknown}"
export ANICCA_EVIDENCE="${3:-}"
export ANICCA_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-self-recover.log"
mkdir -p "$(dirname "$LOG")"

exec python3 "$ANICCA_SHARED_DIR/self-recover-dispatch.py" 2>&1 | tee -a "$LOG"
