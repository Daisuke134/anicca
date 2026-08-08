#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-09-lm-mobile-calendar-oauth.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-mobile-calendar-oauth-pg.XXXXXX")"
DB_NAME="lm_mobile_calendar_oauth_test"
DB_MODE="local"
DOCKER_NAME="lm-mobile-calendar-oauth-pg-$$"

cleanup() {
  if [[ "$DB_MODE" == "docker" ]]; then
    docker rm -f "$DOCKER_NAME" >/dev/null 2>&1 || true
  elif [[ -f "$TEST_TMP/data/postmaster.pid" ]]; then
    pg_ctl -D "$TEST_TMP/data" -m immediate stop >/dev/null 2>&1 || true
  fi
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

if command -v postgres >/dev/null 2>&1; then
  DB_MODE="local"
  mkdir -p "$TEST_TMP/socket"
  initdb -D "$TEST_TMP/data" -A trust --no-locale >/dev/null
  pg_ctl -D "$TEST_TMP/data" -l "$TEST_TMP/postgres.log" -o "-F -h '' -k $TEST_TMP/socket" start >/dev/null
  createdb -h "$TEST_TMP/socket" "$DB_NAME"
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$TEST_TMP/socket" -d "$DB_NAME")
else
  DB_MODE="docker"
  export PGPASSWORD="lm-mobile-calendar-oauth-test-only"
  docker run --rm -d --name "$DOCKER_NAME" -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB_NAME" -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
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
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE TABLE public.lm_users (
  uid text PRIMARY KEY,
  product_locale text NOT NULL DEFAULT 'en',
  calls_enabled boolean NOT NULL DEFAULT false,
  calendar_status text,
  calendar_provider text,
  gmail_account_id text,
  calendar_composio_user_id text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.lm_mobile_oauth_states (
  state_hash text PRIMARY KEY CHECK (length(state_hash) = 64),
  uid text REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  subject_hash text CHECK (subject_hash IS NULL OR length(subject_hash) = 64),
  provider text NOT NULL DEFAULT 'google_calendar',
  redirect_uri text,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
SQL

# Applying the migration itself proves the SQL function is syntactically valid.
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

SUBJECT_HASH="$(printf '%s' 'calendar-subject-a' | sha256sum | cut -d' ' -f1)"

# First link creates one stable LM user and one provider identity mapping.
FIRST="$("${PSQL[@]}" -Atqc "SELECT uid || '|' || product_locale FROM public.link_lm_mobile_calendar_identity('google_calendar','$SUBJECT_HASH','lm_oauth_demo','owner-a','account-a','auth-a','en');")"
[[ "$FIRST" == "lm_oauth_demo|en" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE uid='lm_oauth_demo' AND calendar_status='connected' AND calendar_provider='composio_gcal' AND calendar_composio_user_id='owner-a' AND gmail_account_id='account-a';")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_mobile_calendar_connections WHERE provider='google_calendar' AND provider_subject_hash='$SUBJECT_HASH' AND uid='lm_oauth_demo' AND composio_user_id='owner-a' AND connected_account_id='account-a' AND auth_config_id='auth-a';")" == "1" ]]

# A reconnect with the same provider subject keeps the stable UID while
# refreshing the provider routing facts.
SECOND="$("${PSQL[@]}" -Atqc "SELECT uid || '|' || product_locale FROM public.link_lm_mobile_calendar_identity('google_calendar','$SUBJECT_HASH','lm_other','owner-b','account-b','auth-b','ja');")"
[[ "$SECOND" == "lm_oauth_demo|en" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE uid='lm_oauth_demo' AND calendar_composio_user_id='owner-b' AND gmail_account_id='account-b';")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE uid='lm_other';")" == "0" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_mobile_calendar_connections WHERE provider='google_calendar' AND provider_subject_hash='$SUBJECT_HASH' AND uid='lm_oauth_demo' AND composio_user_id='owner-b' AND connected_account_id='account-b' AND auth_config_id='auth-b';")" == "1" ]]

# A deployment retry must recreate the function without changing the mapping.
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE uid='lm_oauth_demo';")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_mobile_calendar_connections WHERE provider_subject_hash='$SUBJECT_HASH';")" == "1" ]]

printf '%s\n' 'mobile-calendar-oauth-postgres: PASS migration_apply=1 first_link=1 stable_uid_reconnect=1 routing_updated=1 rerun=1'
