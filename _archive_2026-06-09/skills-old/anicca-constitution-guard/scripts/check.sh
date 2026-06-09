#!/usr/bin/env bash
# anicca-constitution-guard — bash wrapper for check.py.
# Usage:
#   ./check.sh --action "<free text describing the side-effectful action>"
# Exit codes mirror check.py: 0 OK, 2 rule BLOCKED, 3 hash BLOCKED, 4 usage.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
exec /opt/homebrew/bin/python3 "$SKILL/scripts/check.py" "$@"
