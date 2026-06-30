#!/usr/bin/env bash
# loop-roi.sh — REQ-B1 end-of-pass roi.jsonl row writer.
# SECURITY: all params via ENV VAR, never heredoc-interpolated. FIND-2-001 fix.
#
# Usage: loop-roi.sh <slot> <pass_id> <tokens_in> <tokens_out> <model_id> <wall_seconds>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_PASS_ID="${2:-}"
export ANICCA_TOKENS_IN="${3:-0}"
export ANICCA_TOKENS_OUT="${4:-0}"
export ANICCA_MODEL_ID="${5:-sonnet}"
export ANICCA_WALL_S="${6:-0}"
export ANICCA_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$ANICCA_SHARED_DIR/loop-roi-dispatch.py"
