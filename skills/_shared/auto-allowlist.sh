#!/usr/bin/env bash
# auto-allowlist.sh — REQ-H3e hook auto-allowlist (sprint-2).
# Reads trusted-authors.json; firecrawl npmjs; auto-PR safe modules.
# NO human-touch.
#
# Usage: auto-allowlist.sh <slot> <module-name>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_MODULE="${2:-}"
LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-auto-allowlist.log"
mkdir -p "$(dirname "$LOG")"

# Sprint-2 cycle 2 wires the firecrawl + trust-score evaluation + auto-PR flow.
# Scaffold: log + exit. The slot continues without the missing module.
echo "$(date '+%F %T') auto-allowlist: scaffold for module $ANICCA_MODULE (cycle 2 wires real)" >> "$LOG"
exit 1  # scaffold returns failure → health-check skips module per REQ-H3e(iv)
