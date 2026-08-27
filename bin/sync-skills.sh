#!/usr/bin/env bash
# sync-skills.sh — REQ-VENDOR-002: deterministic vendor copy from skills.lock. Without --update,
# verifies every vendored copy's checksum still matches skills.lock (exit non-zero on drift, never
# silently accepted). With --update, overwrites the vendored copy from the pinned source_commit and
# rewrites skills.lock's source_commit/sha256 for every entry.
#
#   bash sync-skills.sh [--update]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3

"$PY" "$HERE/bin/sync_skills.py" "$@"
