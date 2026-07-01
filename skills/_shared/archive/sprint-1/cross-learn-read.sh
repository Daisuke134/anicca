#!/usr/bin/env bash
# cross-learn-read.sh — REQ-D1 PRE-STEP: read peer lessons from gh issues.
#
# Usage: cross-learn-read.sh <slot>
# Returns JSON to stdout; gh failure → empty list (REQ-D3 graceful).
set -uo pipefail

SLOT="${1:-}"
gh issue list --label "${SLOT}-lesson" --label "earning-skill-proposal" \
   --limit 20 --json number,title,body,createdAt 2>/dev/null || echo "[]"
