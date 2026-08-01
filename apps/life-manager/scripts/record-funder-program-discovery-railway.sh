#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "usage: record-funder-program-discovery-railway <assessment.json>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAILWAY_SERVICE="${LIFE_MANAGER_POSTGRES_SERVICE:-Postgres-1nl0}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

{
  printf '\\set ON_ERROR_STOP on\n\\pset tuples_only on\n\\pset format unaligned\n'
  printf "SELECT coalesce(json_agg(row_to_json(current_rows)),'[]'::json) FROM (SELECT DISTINCT ON (funder_id) funder_id,official_url,priority,discovery_facts_digest FROM public.lm_funder_registry_snapshots WHERE tenant_id='dais-local' ORDER BY funder_id,observed_at DESC,recorded_at DESC) current_rows;\n"
} | railway connect "$RAILWAY_SERVICE" | awk '/^\[/{print; exit}' > "$TEMP_DIR/existing.json"
jq -e 'type == "array"' "$TEMP_DIR/existing.json" >/dev/null

node "$SCRIPT_DIR/render-funder-program-discovery-sql.js" --input "$1" --existing "$TEMP_DIR/existing.json" > "$TEMP_DIR/insert.sql"
railway connect "$RAILWAY_SERVICE" < "$TEMP_DIR/insert.sql"
