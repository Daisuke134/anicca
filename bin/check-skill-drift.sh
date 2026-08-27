#!/usr/bin/env bash
# check-skill-drift.sh — REQ-VENDOR-003: read-only drift auditor. Recomputes sha256 for every
# skills.lock-vendored path and reports ok/DRIFT per entry without modifying any file.
#
#   bash check-skill-drift.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3

"$PY" "$HERE/bin/check_skill_drift.py"
