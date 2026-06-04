#!/usr/bin/env bash
# Appends one JSON line to ~/.hermes/state/colony.jsonl.
# Usage: append.sh <child_id> <host> <sandbox_id> <address> <constitution_sha> <status> [child_home]
# Idempotent per-line; never modifies existing rows. Locks via flock if available.
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"
COLONY="${COLONY:-/Users/anicca/.hermes/state/colony.jsonl}"
mkdir -p "$(dirname "$COLONY")"
touch "$COLONY"

[ $# -ge 6 ] || { echo "append.sh: need >=6 args, got $#" >&2; exit 64; }
child_id="$1"; host="$2"; sandbox_id="$3"; address="$4"; sha="$5"; status="$6"
child_home="${7:-/home/daytona}"
ts=$(date -u +%FT%TZ)

LINE=$("$JQ" -nc \
  --arg child_id "$child_id" \
  --arg host "$host" \
  --arg sandbox_id "$sandbox_id" \
  --arg address "$address" \
  --arg spawned_at "$ts" \
  --arg constitution_sha "$sha" \
  --arg status "$status" \
  --arg child_home "$child_home" \
  --arg parent_address "$("$JQ" -r '.address // "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"' /Users/anicca/.hermes/state/wallet.json 2>/dev/null)" \
  '{child_id:$child_id, host:$host, sandbox_id:$sandbox_id, address:$address,
    parent_address:$parent_address, spawned_at:$spawned_at,
    constitution_sha:$constitution_sha, status:$status, child_home:$child_home, generation:1}')

if command -v flock >/dev/null 2>&1; then
  ( flock 9; printf '%s\n' "$LINE" >> "$COLONY" ) 9>"$COLONY.lock"
else
  printf '%s\n' "$LINE" >> "$COLONY"
fi
echo "$LINE"
