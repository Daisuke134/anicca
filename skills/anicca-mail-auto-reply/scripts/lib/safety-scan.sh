#!/usr/bin/env bash
# safety-scan.sh — FR-006 forbidden-substring blocker for reply drafts.
#
# Reads a draft body from stdin and exits:
#   0 = safe (no forbidden substrings, length within 30..2500 chars)
#   1 = unsafe (any forbidden substring OR length violation)
#
# Stderr carries a single-line reason when blocking, for upstream logging.

set -uo pipefail

BODY=$(cat)

FORBIDDEN=(
  '[記入]'
  '[fill in]'
  '[TBD]'
  '[未定]'
  '[name]'
  '[NAME]'
  'on behalf of Daisuke'
  'on behalf of Daisuke Narita'
  '+1 (336)'
  '+1 336'
)

for s in "${FORBIDDEN[@]}"; do
  if printf '%s' "$BODY" | grep -qF "$s"; then
    echo "[safety-scan] BLOCK · forbidden substring present: '$s'" >&2
    exit 1
  fi
done

# Length bounds: trim trailing/leading whitespace before counting.
LEN=$(printf '%s' "$BODY" | wc -c | tr -d ' ')
if [ "$LEN" -lt 30 ]; then
  echo "[safety-scan] BLOCK · body too short ($LEN < 30)" >&2
  exit 1
fi
if [ "$LEN" -gt 2500 ]; then
  echo "[safety-scan] BLOCK · body too long ($LEN > 2500)" >&2
  exit 1
fi

exit 0
