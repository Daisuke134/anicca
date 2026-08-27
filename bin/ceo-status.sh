#!/usr/bin/env bash
# ceo-status.sh — REQ-CEO-007: per-loop status/allocation/cadence/evidence/cost/revenue/budget
# report. Ensures the 4 CEO ledgers exist (REQ-CEO-005), then reads+renders. Always exits 0.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
BASE="${CEO_STATE_DIR:-$HERE}"

"$PY" "$HERE/bin/ceo_status.py" "$BASE"
exit 0
