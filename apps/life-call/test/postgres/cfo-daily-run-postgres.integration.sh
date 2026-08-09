#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-09-cfo-daily-runs.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/cfo-daily-run-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="cfo_daily_run_test"
DB_MODE="local"
DOCKER_NAME="cfo-daily-run-pg-$$"
A_PID=""
B_PID=""

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$A_PID" ]] && kill -0 "$A_PID" >/dev/null 2>&1; then
    kill "$A_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$B_PID" ]] && kill -0 "$B_PID" >/dev/null 2>&1; then
    kill "$B_PID" >/dev/null 2>&1 || true
  fi
  if [[ "$DB_MODE" == "docker" ]]; then
    docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true
  elif [[ -f "$PGDATA_DIR/postmaster.pid" ]]; then
    pg_ctl -D "$PGDATA_DIR" -m immediate stop >/dev/null 2>&1 || true
  fi
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

if command -v postgres >/dev/null 2>&1 && postgres --version | grep -Eq 'PostgreSQL (1[89]|[2-9][0-9])\.'; then
  mkdir -p "$PGSOCKET_DIR"
  initdb -D "$PGDATA_DIR" -A trust --no-locale >/dev/null
  pg_ctl -D "$PGDATA_DIR" -l "$PGLOG" -o "-F -h '' -k $PGSOCKET_DIR" start >/dev/null
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$DB_NAME")
  createdb -h "$PGSOCKET_DIR" "$DB_NAME"
else
  DB_MODE="docker"
  export PGPASSWORD="cfo-daily-run-test-only"
  docker run --rm -d --name "$DOCKER_NAME" \
    -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB_NAME" \
    -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
  MAPPED=""
  for _ in {1..100}; do
    MAPPED="$(docker port "$DOCKER_NAME" 5432/tcp 2>/dev/null || true)"
    [[ -n "$MAPPED" ]] && break
    sleep 0.1
  done
  [[ -n "$MAPPED" ]] || fail 'postgres container did not expose a port'
  PGPORT="${MAPPED##*:}"
  for _ in {1..100}; do
    pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null 2>&1 && break
    sleep 0.1
  done
  pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME")
fi

# A minimal synthetic version of the existing snapshot lifecycle is enough to
# exercise the additive daily-run migration without connecting to a live DB.
"${PSQL[@]}" >/dev/null <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE TABLE public.lm_users (
  uid text PRIMARY KEY
);
CREATE TABLE public.lm_panel_preferences (
  uid text PRIMARY KEY REFERENCES public.lm_users(uid),
  call_time_zone text NOT NULL
);
CREATE TABLE public.lm_cfo_daily_snapshots (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  uid text NOT NULL REFERENCES public.lm_users(uid),
  reporting_date date NOT NULL,
  run_id uuid NOT NULL,
  report_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_bundle jsonb NOT NULL DEFAULT '{}'::jsonb
);
GRANT SELECT, UPDATE ON TABLE public.lm_panel_preferences TO service_role;
SQL

run_migration_expect_failure() {
  local label="$1"
  local expected="$2"
  local wrapper="$TEST_TMP/${label}-transaction.sql"
  local error_file="$TEST_TMP/${label}.err"
  {
    printf 'BEGIN;\n'
    cat "$MIGRATION"
    printf '\nCOMMIT;\n'
  } >"$wrapper"
  if "${PSQL[@]}" -f "$wrapper" >"$TEST_TMP/${label}.out" 2>"$error_file"; then
    fail "$label migration unexpectedly committed"
  fi
  grep -Fq "ERROR:  $expected" "$error_file" || fail "$label migration returned an unexpected error"
  [[ "$(${PSQL[@]} -Atqc "SELECT to_regclass('public.lm_cfo_daily_runs') IS NULL;")" == 't' ]] \
    || fail "$label migration left its run table behind"
  [[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_proc WHERE pronamespace = 'public'::regnamespace AND proname IN ('lm_claim_cfo_daily_run', 'lm_cfo_owner_local_date');")" == '0' ]] \
    || fail "$label migration left a function behind"
  [[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conname = 'lm_cfo_daily_snapshots_daily_run_fk';")" == '0' ]] \
    || fail "$label migration left its snapshot FK behind"
}

MISSING_RUN='20000000-0000-4000-8000-000000000001'
INVALID_RUN='20000000-0000-4000-8000-000000000002'
BACKFILL_RUN='20000000-0000-4000-8000-000000000003'

# A missing owner preference must abort the whole migration transaction.
"${PSQL[@]}" >/dev/null <<SQL
INSERT INTO public.lm_users(uid) VALUES ('tenant-missing');
INSERT INTO public.lm_cfo_daily_snapshots(uid, reporting_date, run_id)
VALUES ('tenant-missing', DATE '2026-08-09', '$MISSING_RUN'::uuid);
SQL
run_migration_expect_failure missing_timezone cfo_daily_run_migration_requires_valid_timezone_preference
"${PSQL[@]}" >/dev/null <<'SQL'
DELETE FROM public.lm_cfo_daily_snapshots WHERE uid = 'tenant-missing';
DELETE FROM public.lm_users WHERE uid = 'tenant-missing';
SQL

# A preference that is not in pg_timezone_names must fail identically and leave
# no partial table, function, or constraint behind.
"${PSQL[@]}" >/dev/null <<SQL
INSERT INTO public.lm_users(uid) VALUES ('tenant-invalid');
INSERT INTO public.lm_panel_preferences(uid, call_time_zone) VALUES ('tenant-invalid', 'Not/A/Zone');
INSERT INTO public.lm_cfo_daily_snapshots(uid, reporting_date, run_id)
VALUES ('tenant-invalid', DATE '2026-08-09', '$INVALID_RUN'::uuid);
SQL
run_migration_expect_failure invalid_timezone cfo_daily_run_migration_requires_valid_timezone_preference
"${PSQL[@]}" >/dev/null <<'SQL'
DELETE FROM public.lm_cfo_daily_snapshots WHERE uid = 'tenant-invalid';
DELETE FROM public.lm_panel_preferences WHERE uid = 'tenant-invalid';
DELETE FROM public.lm_users WHERE uid = 'tenant-invalid';
SQL

# Seed one existing snapshot for migration backfill and three preference-only
# owners for new claims. All values are synthetic and have no live identifiers.
"${PSQL[@]}" >/dev/null <<SQL
INSERT INTO public.lm_users(uid) VALUES ('tenant-existing'), ('tenant-claim'), ('tenant-concurrent');
INSERT INTO public.lm_panel_preferences(uid, call_time_zone)
VALUES ('tenant-existing', 'Asia/Tokyo'), ('tenant-claim', 'Asia/Tokyo'), ('tenant-concurrent', 'Asia/Tokyo');
INSERT INTO public.lm_cfo_daily_snapshots(uid, reporting_date, run_id)
VALUES ('tenant-existing', DATE '2026-08-09', '$BACKFILL_RUN'::uuid);
SQL

"${PSQL[@]}" -f "$MIGRATION" >"$TEST_TMP/migration-valid.out" 2>"$TEST_TMP/migration-valid.err" \
  || fail 'valid daily-run migration failed'

BACKFILL="$(${PSQL[@]} -Atqc "SELECT run_id::text || '|' || time_zone || '|' || time_zone_source FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-existing' AND reporting_date = DATE '2026-08-09';")"
[[ "$BACKFILL" == "$BACKFILL_RUN|Asia/Tokyo|migration_preference" ]] \
  || fail 'existing snapshot run_id or migration timezone provenance was not preserved'

if "${PSQL[@]}" -c "INSERT INTO public.lm_cfo_daily_snapshots(uid, reporting_date, run_id) VALUES ('tenant-existing', DATE '2026-08-09', '20000000-0000-4000-8000-000000000004'::uuid);" >"$TEST_TMP/fk.out" 2>"$TEST_TMP/fk.err"; then
  fail 'composite snapshot FK accepted an unknown run'
fi
grep -Fq 'violates foreign key constraint "lm_cfo_daily_snapshots_daily_run_fk"' "$TEST_TMP/fk.err" \
  || fail 'composite snapshot FK returned the wrong rejection'

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lm_cfo_daily_runs'::regclass) THEN
    RAISE EXCEPTION 'daily-run table RLS is disabled';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'INSERT')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'UPDATE')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'DELETE') THEN
    RAISE EXCEPTION 'service-role run-table grants are not append-only';
  END IF;
  IF has_table_privilege('anon', 'public.lm_cfo_daily_runs', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_cfo_daily_runs', 'SELECT') THEN
    RAISE EXCEPTION 'browser run-table SELECT grant present';
  END IF;
  IF NOT has_function_privilege('service_role', 'public.lm_claim_cfo_daily_run(text)', 'EXECUTE')
     OR has_function_privilege('anon', 'public.lm_claim_cfo_daily_run(text)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_claim_cfo_daily_run(text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'claim RPC grants are not service-only';
  END IF;
END $$;
SQL

# The public date helper is intentionally private. ACL inspection covers the
# PUBLIC pseudo-role; SET ROLE proves the three concrete application roles.
PUBLIC_HELPER_GRANT="$(${PSQL[@]} -Atqc "SELECT COALESCE(bool_or(grantee = 0 AND privilege_type = 'EXECUTE'), false) FROM pg_proc AS p LEFT JOIN LATERAL aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) AS privilege ON true WHERE p.oid = 'public.lm_cfo_owner_local_date(text,timestamptz)'::regprocedure;")"
[[ "$PUBLIC_HELPER_GRANT" == 'f' ]] || fail 'PUBLIC can execute the private date helper'
for role in anon authenticated service_role; do
  HELPER_ERR="$TEST_TMP/helper-${role}.err"
  if "${PSQL[@]}" -c "SET ROLE $role; SELECT public.lm_cfo_owner_local_date('Asia/Tokyo', statement_timestamp());" >"$TEST_TMP/helper-${role}.out" 2>"$HELPER_ERR"; then
    fail "$role executed the private date helper"
  fi
  grep -Fq 'permission denied for function lm_cfo_owner_local_date' "$HELPER_ERR" \
    || fail "$role helper rejection was not a permission denial"
done

CLAIM_JSON="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-claim');")"
CLAIM_KEYS="$(${PSQL[@]} -Atqc "SET ROLE service_role; WITH receipt AS (SELECT public.lm_claim_cfo_daily_run('tenant-claim') AS value) SELECT string_agg(key, ',' ORDER BY key) FROM receipt, LATERAL jsonb_object_keys(receipt.value) AS keys(key);")"
[[ "$CLAIM_KEYS" == 'created_at,public_ref,reporting_date,run_id,time_zone' ]] \
  || fail 'claim receipt keys are not exactly the closed five-key projection'
CLAIM_KEY_COUNT="$(${PSQL[@]} -Atqc "SET ROLE service_role; WITH receipt AS (SELECT public.lm_claim_cfo_daily_run('tenant-claim') AS value) SELECT count(*) FROM receipt, LATERAL jsonb_object_keys(receipt.value) AS keys(key);")"
[[ "$CLAIM_KEY_COUNT" == '5' ]] || fail 'claim receipt key count is not five'
CLAIM_PRIVATE_KEYS="$(${PSQL[@]} -Atqc "SET ROLE service_role; WITH receipt AS (SELECT public.lm_claim_cfo_daily_run('tenant-claim') AS value) SELECT count(*) FROM receipt, LATERAL jsonb_object_keys(receipt.value) AS keys(key) WHERE key IN ('uid', 'id', 'time_zone_source', 'report_payload', 'source_bundle');")"
[[ "$CLAIM_PRIVATE_KEYS" == '0' ]] || fail 'claim receipt contains a UID or private column'
[[ "$CLAIM_JSON" == *'"public_ref"'* && "$CLAIM_JSON" == *'"reporting_date"'* && "$CLAIM_JSON" == *'"run_id"'* && "$CLAIM_JSON" == *'"time_zone"'* && "$CLAIM_JSON" == *'"created_at"'* ]] \
  || fail 'claim receipt omitted a required public field'

RETRY_JSON="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-claim');")"
[[ "$CLAIM_JSON" == "$RETRY_JSON" ]] || fail 'same-date service-role retry returned a different run receipt'
CLAIM_SOURCE="$(${PSQL[@]} -Atqc "SELECT time_zone_source FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-claim';")"
[[ "$CLAIM_SOURCE" == 'owner_preference' ]] || fail 'new claim did not record owner_preference provenance'

# Superuser UPDATE/DELETE reach the append-only trigger; service_role has no
# mutation grant and therefore cannot bypass it through the table API.
for operation in UPDATE DELETE; do
  MUTATION_ERR="$TEST_TMP/mutation-${operation}.err"
  if [[ "$operation" == 'UPDATE' ]]; then
    MUTATION_SQL="UPDATE public.lm_cfo_daily_runs SET time_zone = time_zone WHERE uid = 'tenant-claim';"
  else
    MUTATION_SQL="DELETE FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-claim';"
  fi
  if "${PSQL[@]}" -c "$MUTATION_SQL" >"$TEST_TMP/mutation-${operation}.out" 2>"$MUTATION_ERR"; then
    fail "superuser $operation bypassed the daily-run append-only trigger"
  fi
  grep -Fq 'lm_cfo_daily_runs is append-only' "$MUTATION_ERR" \
    || fail "daily-run $operation returned the wrong trigger rejection"
done

# Force two service-role sessions to overlap. Session A holds the preference
# row lock after its claim; session B must wait in the claim RPC and then return
# the exact same run once A commits.
SESSION_A="$TEST_TMP/session-a.sql"
SESSION_B="$TEST_TMP/session-b.sql"
SESSION_A_OUT="$TEST_TMP/session-a.out"
SESSION_B_OUT="$TEST_TMP/session-b.out"
A_APP_NAME='cfo-daily-run-concurrency-a'
B_APP_NAME='cfo-daily-run-concurrency-b'
printf '%s\n' \
  'BEGIN;' \
  'SET ROLE service_role;' \
  "SELECT public.lm_claim_cfo_daily_run('tenant-concurrent')->>'run_id';" \
  'SELECT pg_sleep(4);' \
  'COMMIT;' >"$SESSION_A"
printf '%s\n' \
  'BEGIN;' \
  'SET ROLE service_role;' \
  "SELECT public.lm_claim_cfo_daily_run('tenant-concurrent')->>'run_id';" \
  'COMMIT;' >"$SESSION_B"

PGAPPNAME="$A_APP_NAME" "${PSQL[@]}" -Atqf "$SESSION_A" >"$SESSION_A_OUT" 2>"$TEST_TMP/session-a.err" &
A_PID=$!
HOLDING='0'
A_READY_SQL="SELECT count(*) FROM pg_stat_activity AS activity WHERE activity.pid <> pg_backend_pid() AND activity.application_name = '$A_APP_NAME' AND activity.state = 'active' AND activity.query = 'SELECT pg_sleep(4);' AND activity.wait_event_type = 'Timeout' AND activity.wait_event = 'PgSleep' AND activity.xact_start IS NOT NULL AND EXISTS (SELECT 1 FROM pg_locks AS lock WHERE lock.pid = activity.pid AND lock.granted AND lock.relation = 'public.lm_panel_preferences'::regclass AND lock.mode = 'RowShareLock');"
for _ in {1..100}; do
  HOLDING="$(${PSQL[@]} -Atqc "$A_READY_SQL" | tr -d '[:space:]')"
  [[ "$HOLDING" == '1' ]] && break
  sleep 0.1
done
[[ "$HOLDING" == '1' ]] || fail 'first concurrent claim did not reach its hold point'

PGAPPNAME="$B_APP_NAME" "${PSQL[@]}" -Atqf "$SESSION_B" >"$SESSION_B_OUT" 2>"$TEST_TMP/session-b.err" &
B_PID=$!
LOCK_WAITING='0'
B_WAIT_SQL="SELECT count(*) FROM pg_stat_activity AS waiting WHERE waiting.pid <> pg_backend_pid() AND waiting.application_name = '$B_APP_NAME' AND waiting.state = 'active' AND waiting.wait_event_type = 'Lock' AND waiting.wait_event IS NOT NULL AND waiting.query LIKE '%lm_claim_cfo_daily_run%';"
for _ in {1..100}; do
  LOCK_WAITING="$(${PSQL[@]} -Atqc "$B_WAIT_SQL" | tr -d '[:space:]')"
  [[ "$LOCK_WAITING" != '0' ]] && break
  sleep 0.1
done
[[ "$LOCK_WAITING" != '0' ]] || fail 'second concurrent claim never waited on the first transaction'

A_STATUS=0
B_STATUS=0
wait "$A_PID" || A_STATUS=$?
wait "$B_PID" || B_STATUS=$?
A_PID=''
B_PID=''
[[ "$A_STATUS" == '0' && "$B_STATUS" == '0' ]] || fail 'concurrent claim session failed'
CONCURRENT_A_RUN="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_A_OUT" | head -n 1)"
CONCURRENT_B_RUN="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_B_OUT" | head -n 1)"
[[ "$CONCURRENT_A_RUN" =~ ^[0-9a-f-]{36}$ ]] || fail 'first concurrent claim returned no run_id'
[[ "$CONCURRENT_A_RUN" == "$CONCURRENT_B_RUN" ]] || fail 'concurrent claims returned different run IDs'
CONCURRENT_ROWS="$(${PSQL[@]} -Atqc "SELECT count(*) || '|' || count(DISTINCT run_id) FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-concurrent';")"
[[ "$CONCURRENT_ROWS" == '1|1' ]] || fail 'concurrent claims created more than one row or run'

printf '%s\n' 'cfo-daily-run-postgres: PASS'
