#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-09-06-lm-investment-states.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/investment-state-pg.XXXXXX")"
DB_NAME="investment_state_test"
DOCKER_NAME="investment-state-pg-$$"
DB_MODE="local"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"

cleanup() {
  if [[ "$DB_MODE" == "docker" ]]; then
    docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true
  elif [[ -f "$PGDATA_DIR/postmaster.pid" ]]; then
    pg_ctl -D "$PGDATA_DIR" -m immediate stop >/dev/null 2>&1 || true
  fi
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

if command -v postgres >/dev/null 2>&1; then
  mkdir -p "$PGSOCKET_DIR"
  initdb -D "$PGDATA_DIR" -A trust --no-locale >/dev/null
  pg_ctl -D "$PGDATA_DIR" -l "$PGLOG" -o "-F -h '' -k $PGSOCKET_DIR" start >/dev/null
  createdb -h "$PGSOCKET_DIR" "$DB_NAME"
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$DB_NAME")
else
  DB_MODE="docker"
  export PGPASSWORD="investment-state-test-only"
  docker run --rm -d --name "$DOCKER_NAME" -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB_NAME" -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
  PGPORT="$(docker port "$DOCKER_NAME" 5432/tcp)"; PGPORT="${PGPORT##*:}"
  for _ in {1..100}; do
    pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null 2>&1 && break
    sleep 0.1
  done
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME")
fi

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('tenant-a'), ('tenant-b');
SQL
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.lm_investment_states', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_investment_states', 'SELECT') THEN
    RAISE EXCEPTION 'browser grant present';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_investment_states', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_investment_states', 'INSERT')
     OR NOT has_table_privilege('service_role', 'public.lm_investment_states', 'UPDATE') THEN
    RAISE EXCEPTION 'service role contract absent';
  END IF;
END $$;

SET ROLE service_role;
INSERT INTO public.lm_investment_states (
  uid, lifecycle, deployment, mode, paused, killed, core_digest, receipt_refs,
  alpaca_api_key_ref, alpaca_api_secret_ref
) VALUES (
  'tenant-a', 'in_review', 'cloud', 'paper', false, false, repeat('a', 64),
  '["provider-receipt://alpaca/application/abc"]',
  'secret://alpaca/api-key', 'secret://alpaca/api-secret'
);
RESET ROLE;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT * FROM public.lm_investment_states;" >/dev/null 2>&1; then
  echo 'FAIL anon read Investment state' >&2; exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_investment_states(uid,lifecycle,deployment,mode,alpaca_api_secret_ref) VALUES ('tenant-b','active','cloud','live','raw-secret');" >/dev/null 2>&1; then
  echo 'FAIL raw Alpaca secret accepted' >&2; exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_investment_states(uid,lifecycle,deployment,mode) VALUES ('tenant-b','unknown','cloud','paper');" >/dev/null 2>&1; then
  echo 'FAIL unknown lifecycle accepted' >&2; exit 1
fi

ROWS="$("${PSQL[@]}" -Atqc "SELECT uid||','||lifecycle||','||deployment||','||mode FROM public.lm_investment_states ORDER BY uid;")"
[[ "$ROWS" == "tenant-a,in_review,cloud,paper" ]]
echo 'investment-state-postgres: PASS migration_twice=2 tenants=1 browser_access=0 raw_secret=0'
