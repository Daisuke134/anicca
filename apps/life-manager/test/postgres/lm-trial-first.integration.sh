#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION_REL="migrations/2026-08-28-lm-trial-first.sql"
MIGRATION="$ROOT_DIR/$MIGRATION_REL"
CORE_MIGRATION="$ROOT_DIR/migrations/2026-08-27-lm-panel-onboarding-core.sql"
if [[ ! -f "$MIGRATION" ]]; then
  printf 'missing migration: %s\n' "$MIGRATION_REL" >&2
  exit 1
fi
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-trial-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="lm_trial_test"
DB_MODE="local"
DOCKER_NAME="lm-trial-pg-$$"

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
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$DB_NAME")
  createdb -h "$PGSOCKET_DIR" "$DB_NAME"
else
  DB_MODE="docker"
  export PGPASSWORD="lm-trial-test-only"
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
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE TABLE public.lm_users(
  uid text PRIMARY KEY,
  telegram_chat_id text,
  tg_onboard_stage text,
  name text,
  calendar_provider text,
  home_address text,
  phone text,
  paid boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.lm_panel_preferences(
  uid text PRIMARY KEY,
  notifications_enabled boolean NOT NULL DEFAULT false,
  call_enabled boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now()
);
SQL

"${PSQL[@]}" -f "$CORE_MIGRATION" >/dev/null

"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_users(
  uid, telegram_chat_id, tg_onboard_stage, name, calendar_provider, home_address, phone, paid
) VALUES (
  'tenant-a', '101', 'notifications', 'Aiko', 'composio_gcal', 'Tokyo', NULL, false
);
INSERT INTO public.lm_panel_preferences(uid, notifications_enabled, call_enabled)
VALUES ('tenant-a', false, false);
SQL

INITIAL_STATE="$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT (public.lm_panel_onboarding_state('tenant-a', '101')->>'trialExpiresAt') IS NULL, (public.lm_panel_onboarding_state('tenant-a', '101')->>'trialActive')::boolean = false;")"
[[ "$INITIAL_STATE" == "t|t" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE FUNCTION public.lm_trial_test_reject_paid_update()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'paid update forbidden';
END;
$$;
CREATE TRIGGER lm_trial_test_no_paid_updates
BEFORE UPDATE OF paid ON public.lm_users
FOR EACH ROW EXECUTE FUNCTION public.lm_trial_test_reject_paid_update();
SQL

BEFORE_GRANT="$("${PSQL[@]}" -Atqc "SELECT clock_timestamp();")"
"${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_transition('tenant-a', '101', 'notifications.enable', '{}'::jsonb);" >/dev/null
AFTER_GRANT="$("${PSQL[@]}" -Atqc "SELECT clock_timestamp();")"
FIRST_EXPIRES="$("${PSQL[@]}" -Atqc "SELECT trial_expires_at::text FROM public.lm_users WHERE uid = 'tenant-a';")"
[[ -n "$FIRST_EXPIRES" ]]
GRANT_WINDOW="$("${PSQL[@]}" -Atqc "SELECT trial_expires_at >= '$BEFORE_GRANT'::timestamptz + interval '3 days' AND trial_expires_at <= '$AFTER_GRANT'::timestamptz + interval '3 days' FROM public.lm_users WHERE uid = 'tenant-a';")"
[[ "$GRANT_WINDOW" == "t" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
UPDATE public.lm_users
SET tg_onboard_stage = 'notifications', updated_at = now()
WHERE uid = 'tenant-a';
UPDATE public.lm_panel_preferences
SET notifications_enabled = false, call_enabled = false, updated_at = now()
WHERE uid = 'tenant-a';
SQL

"${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_transition('tenant-a', '101', 'notifications.enable', '{}'::jsonb);" >/dev/null
SECOND_EXPIRES="$("${PSQL[@]}" -Atqc "SELECT trial_expires_at::text FROM public.lm_users WHERE uid = 'tenant-a';")"
[[ "$FIRST_EXPIRES" == "$SECOND_EXPIRES" ]]

STATE_CHECK="$("${PSQL[@]}" -Atqc "SELECT (public.lm_panel_onboarding_state('tenant-a', '101')->>'trialExpiresAt')::timestamptz = trial_expires_at, (public.lm_panel_onboarding_state('tenant-a', '101')->>'trialActive')::boolean, paid = false FROM public.lm_users WHERE uid = 'tenant-a';")"
[[ "$STATE_CHECK" == "t|t|t" ]]

"${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_transition('tenant-a', '101', 'phone.skip', '{}'::jsonb);" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT tg_onboard_stage FROM public.lm_users WHERE uid = 'tenant-a';")" == "done" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
UPDATE public.lm_users
SET tg_onboard_stage = 'call', phone = '+12025550123', updated_at = now()
WHERE uid = 'tenant-a';
UPDATE public.lm_panel_preferences
SET notifications_enabled = true, call_enabled = false, updated_at = now()
WHERE uid = 'tenant-a';
SQL
"${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_transition('tenant-a', '101', 'call.enable', '{}'::jsonb);" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT tg_onboard_stage FROM public.lm_users WHERE uid = 'tenant-a';")" == "done" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
UPDATE public.lm_users
SET tg_onboard_stage = 'call', updated_at = now()
WHERE uid = 'tenant-a';
UPDATE public.lm_panel_preferences
SET call_enabled = true, updated_at = now()
WHERE uid = 'tenant-a';
SQL
"${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_transition('tenant-a', '101', 'call.skip', '{}'::jsonb);" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT tg_onboard_stage FROM public.lm_users WHERE uid = 'tenant-a';")" == "done" ]]

[[ "$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_onboarding_state('tenant-a', '202') IS NULL;")" == "t" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF NOT has_function_privilege('service_role', 'public.lm_panel_onboarding_state(text,text)', 'EXECUTE')
     OR NOT has_function_privilege('service_role', 'public.lm_panel_onboarding_transition(text,text,text,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service role execute grant absent';
  END IF;
  IF has_function_privilege('anon', 'public.lm_panel_onboarding_state(text,text)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_panel_onboarding_state(text,text)', 'EXECUTE')
     OR has_function_privilege('anon', 'public.lm_panel_onboarding_transition(text,text,text,jsonb)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_panel_onboarding_transition(text,text,text,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser execute grant present';
  END IF;
END $$;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT public.lm_panel_onboarding_state('tenant-a', '101');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL anon executed onboarding state RPC' >&2
  exit 1
fi

printf '%s\n' 'lm-trial-first-postgres: PASS grant_once=1 trial_active=1 tenant_scope=1 acl=1 paid_writes=0'
