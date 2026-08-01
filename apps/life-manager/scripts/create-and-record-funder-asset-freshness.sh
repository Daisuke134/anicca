#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="$(mktemp -d)";trap 'rm -rf "$TEMP_DIR"' EXIT
node "$SCRIPT_DIR/create-funder-asset-freshness-gate.js" "$@" --output "$TEMP_DIR/gate.json"
bash "$SCRIPT_DIR/record-funder-asset-freshness-railway.sh" "$TEMP_DIR/gate.json"
if [[ -n "${FUNDER_ASSET_FRESHNESS_OUTPUT:-}" ]]; then install -m 0600 "$TEMP_DIR/gate.json" "$FUNDER_ASSET_FRESHNESS_OUTPUT"; fi
