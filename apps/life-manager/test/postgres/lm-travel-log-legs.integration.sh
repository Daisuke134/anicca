#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_MIGRATION="$ROOT_DIR/migrations/2026-06-24-ch1-atomic-dedup.sql"
MIGRATION="$ROOT_DIR/migrations/2026-08-28-lm-travel-log-legs.sql"
if [[ ! -f "$BASE_MIGRATION" || ! -f "$MIGRATION" ]]; then
  printf '%s\n' 'missing travel-log migration' >&2
  exit 1
fi

TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-travel-legs-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="lm_travel_legs_test"
DB_MODE="local"
DOCKER_NAME="lm-travel-legs-pg-$$"

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
  export PGPASSWORD="lm-travel-legs-test-only"
  docker run --rm -d --name "$DOCKER_NAME" \
    -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB_NAME" \
    -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
  MAPPED="$(docker port "$DOCKER_NAME" 5432/tcp)"
  PGPORT="${MAPPED##*:}"
  for _ in {1..100}; do
    pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null 2>&1 && break
    sleep 0.1
  done
  pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME")
fi

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE TABLE public.lm_ask_log (
  uid text NOT NULL,
  event_id text NOT NULL
);
SQL

"${PSQL[@]}" -f "$BASE_MIGRATION" >/dev/null

if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'before', 'telegram-t5');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL telegram-t5 accepted before leg migration' >&2
  exit 1
fi

"${PSQL[@]}" >/dev/null <<'SQL'
ALTER TABLE public.lm_travel_log
  ADD CONSTRAINT lm_travel_log_uid_nonempty CHECK (uid <> '');
INSERT INTO public.lm_travel_log(uid, event_key, leg)
VALUES ('tenant-a', 'existing-go', 'go'), ('tenant-a', 'existing-return', 'return');
SQL

"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_travel_log(uid, event_key, leg)
VALUES
  ('tenant-a', 'trial', 'go'),
  ('tenant-a', 'trial', 'return'),
  ('tenant-a', 'trial', 'telegram-t5'),
  ('tenant-a', 'trial', 'trial-upgrade');
SQL

if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'trial', 'unknown-leg');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL unknown travel leg accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'trial', 'trial-upgrade');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL duplicate (uid,event_key,leg) accepted' >&2
  exit 1
fi

LEG_CHECK="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid = 'public.lm_travel_log'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'public.lm_travel_log'::regclass AND attname = 'leg')]::smallint[] AND conname = 'lm_travel_log_leg_check';")"
[[ "$LEG_CHECK" == "1" ]]
VALIDATED="$("${PSQL[@]}" -Atqc "SELECT convalidated FROM pg_constraint WHERE conname = 'lm_travel_log_leg_check';")"
[[ "$VALIDATED" == "t" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_travel_log WHERE event_key IN ('existing-go', 'existing-return');")" == "2" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_constraint WHERE conname = 'lm_travel_log_uid_nonempty';")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lm_travel_log'::regclass;")" == "t" ]]

printf '%s\n' 'lm-travel-log-legs-postgres: PASS pre_migration_reject=1 allowed_legs=4 unknown_reject=1 unique=1 rerun=1 rows=preserved rls=1'
