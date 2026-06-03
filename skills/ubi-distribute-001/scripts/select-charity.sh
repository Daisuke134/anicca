#!/usr/bin/env bash
# select-charity.sh — emits this month's UBI recipient address on stdout.
#
# Order of precedence:
#   1. ~/.openclaw/state/ubi-override.json `.recipient_address` (manual choice)
#   2. charities.json[month_of_year % len(charities)] (rotation)
#
# stdout = exactly one EVM address (lowercase or checksummed). Anything else
# goes to stderr so the address can be piped into `xargs payout.sh`.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHARITIES="$SKILL_DIR/charities.json"
OVERRIDE="${UBI_OVERRIDE_FILE:-$HOME/.openclaw/state/ubi-override.json}"

if [[ ! -f "$CHARITIES" ]]; then
  echo "[select-charity] missing charities.json at $CHARITIES" >&2
  exit 2
fi

# 1. Manual override wins if present.
if [[ -f "$OVERRIDE" ]]; then
  addr=$(jq -r '.recipient_address // empty' "$OVERRIDE" 2>/dev/null || true)
  if [[ -n "$addr" && "$addr" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    name=$(jq -r '.charity_name // "unnamed"' "$OVERRIDE")
    echo "[select-charity] using override: $name" >&2
    echo "$addr"
    exit 0
  fi
  echo "[select-charity] override file present but invalid recipient_address — falling back to rotation" >&2
fi

# 2. Month-of-year rotation.
month=$(date +%-m)            # 1..12 (no leading zero)
len=$(jq 'length' "$CHARITIES")
if [[ -z "$len" || "$len" -le 0 ]]; then
  echo "[select-charity] charities.json is empty" >&2
  exit 3
fi
idx=$(( (month - 1) % len ))
name=$(jq -r ".[$idx].name" "$CHARITIES")
addr=$(jq -r ".[$idx].base_addr" "$CHARITIES")

if [[ ! "$addr" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
  echo "[select-charity] charity #$idx has malformed base_addr: $addr" >&2
  exit 4
fi

echo "[select-charity] month=$month idx=$idx -> $name ($addr)" >&2
echo "$addr"
