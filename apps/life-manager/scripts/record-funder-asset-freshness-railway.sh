#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 || ! -f "$1" ]]; then echo "usage: record-funder-asset-freshness-railway <gate.json>" >&2; exit 2; fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAILWAY_PROJECT_ID="${LIFE_MANAGER_RAILWAY_PROJECT_ID:-f9c524cb-ba4a-43bb-9639-ff736afd9ec1}"
RAILWAY_ENVIRONMENT="${LIFE_MANAGER_RAILWAY_ENVIRONMENT:-production}"
RAILWAY_SERVICE="${LIFE_MANAGER_POSTGRES_SERVICE:-Postgres-1nl0}"
TEMP_DIR="$(mktemp -d)";trap 'rm -rf "$TEMP_DIR"' EXIT
node "$SCRIPT_DIR/render-funder-asset-freshness-sql.js" "$1" > "$TEMP_DIR/gate.sql"
railway connect -p "$RAILWAY_PROJECT_ID" -e "$RAILWAY_ENVIRONMENT" "$RAILWAY_SERVICE" < "$TEMP_DIR/gate.sql"
