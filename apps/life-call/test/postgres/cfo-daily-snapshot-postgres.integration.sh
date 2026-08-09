#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-09-cfo-daily-snapshots.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/cfo-daily-snapshot-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="cfo_daily_snapshot_test"
DB_MODE="local"
DOCKER_NAME="cfo-daily-snapshot-pg-$$"

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

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
  export PGPASSWORD="cfo-daily-snapshot-test-only"
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
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('tenant-a'), ('tenant-b');
SQL

"${PSQL[@]}" -f "$MIGRATION" >/dev/null 2>&1

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.lm_cfo_daily_snapshots', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_cfo_daily_snapshots', 'SELECT') THEN
    RAISE EXCEPTION 'browser table SELECT grant present';
  END IF;
  IF has_function_privilege('anon', 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser snapshot RPC EXECUTE grant present';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', 'INSERT')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', 'UPDATE')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', 'DELETE') THEN
    RAISE EXCEPTION 'service role table privileges do not match';
  END IF;
  IF NOT has_function_privilege('service_role', 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service role snapshot RPC EXECUTE grant absent';
  END IF;
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lm_cfo_daily_snapshots'::regclass) THEN
    RAISE EXCEPTION 'snapshot table RLS is disabled';
  END IF;
END $$;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT count(*) FROM public.lm_cfo_daily_snapshots;" >/dev/null 2>&1; then
  fail 'anon read snapshot table'
fi
if "${PSQL[@]}" -c "SET ROLE authenticated; SELECT count(*) FROM public.lm_cfo_daily_snapshots;" >/dev/null 2>&1; then
  fail 'authenticated read snapshot table'
fi
if "${PSQL[@]}" -c "SET ROLE anon; SELECT public.lm_append_cfo_daily_snapshot('tenant-a', DATE '2026-08-09', '20000000-0000-4000-8000-000000000001'::uuid, '{}'::jsonb, '{}'::jsonb);" >/dev/null 2>&1; then
  fail 'anon executed snapshot RPC'
fi
if "${PSQL[@]}" -c "SET ROLE authenticated; SELECT public.lm_append_cfo_daily_snapshot('tenant-a', DATE '2026-08-09', '20000000-0000-4000-8000-000000000001'::uuid, '{}'::jsonb, '{}'::jsonb);" >/dev/null 2>&1; then
  fail 'authenticated executed snapshot RPC'
fi

append_sql() {
  local uid="$1"
  local reporting_date="$2"
  local run_id="$3"
  local report_payload="$4"
  local source_bundle="$5"
  "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot('$uid', DATE '$reporting_date', '$run_id'::uuid, \$json\$${report_payload}\$json\$::jsonb, \$json\$${source_bundle}\$json\$::jsonb)->>'public_ref';"
}

expect_rpc_error() {
  local label="$1"
  local expected="$2"
  local uid="$3"
  local reporting_date="$4"
  local run_id="$5"
  local report_payload="$6"
  local source_bundle="$7"
  local error_file="$TEST_TMP/rpc-${label}.err"
  if append_sql "$uid" "$reporting_date" "$run_id" "$report_payload" "$source_bundle" > /dev/null 2>"$error_file"; then
    fail "$label accepted"
  fi
  grep -Fq "ERROR:  $expected" "$error_file" || fail "$label returned the wrong error"
}

BASE_DATE='2026-08-09'
BASE_RUN='20000000-0000-4000-8000-000000000001'
BASE_REPORT='{"reportingDate":"2026-08-09","revision":1,"currency":"JPY","fixture":"synthetic"}'
BASE_SOURCE='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"synthetic"}'

FIRST_REF="$(append_sql tenant-a "$BASE_DATE" "$BASE_RUN" "$BASE_REPORT" "$BASE_SOURCE")"
[[ "$FIRST_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'service_role RPC did not return a public_ref'
RETRY_REF="$(append_sql tenant-a "$BASE_DATE" "$BASE_RUN" "$BASE_REPORT" "$BASE_SOURCE")"
[[ "$FIRST_REF" == "$RETRY_REF" ]] || fail 'identical retry changed public_ref'

SERVICE_RECEIPT="$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public_ref::text || '|' || reporting_date::text || '|' || revision::text FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$BASE_DATE';")"
[[ "$SERVICE_RECEIPT" == "$FIRST_REF|$BASE_DATE|1" ]] || fail 'service_role could not select the receipt'
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$BASE_DATE';")" == '1' ]] || fail 'identical retry created another row'

REPORT_CONFLICT='{"reportingDate":"2026-08-09","revision":1,"currency":"JPY","fixture":"different-report"}'
SOURCE_CONFLICT='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"different-source"}'
expect_rpc_error run_id_report_conflict run_id_conflict tenant-a "$BASE_DATE" "$BASE_RUN" "$REPORT_CONFLICT" "$BASE_SOURCE"
expect_rpc_error run_id_source_conflict run_id_conflict tenant-a "$BASE_DATE" "$BASE_RUN" "$BASE_REPORT" "$SOURCE_CONFLICT"

DIFFERENT_RUN='20000000-0000-4000-8000-000000000002'
expect_rpc_error reporting_date_conflict reporting_date_conflict tenant-a "$BASE_DATE" "$DIFFERENT_RUN" "$BASE_REPORT" "$BASE_SOURCE"

direct_insert() {
  local direct_uid="$1"
  local direct_date="$2"
  local run_id="$3"
  local revision="$4"
  local report_payload="$5"
  local source_bundle="$6"
  "${PSQL[@]}" -c "SET ROLE service_role; INSERT INTO public.lm_cfo_daily_snapshots (uid, reporting_date, run_id, revision, report_payload, source_bundle) VALUES ('$direct_uid', DATE '$direct_date', '$run_id'::uuid, $revision, \$json\$${report_payload}\$json\$::jsonb, \$json\$${source_bundle}\$json\$::jsonb);"
}

expect_direct_rejected() {
  local label="$1"
  local direct_date="$2"
  local run_id="$3"
  local revision="$4"
  local report_payload="$5"
  local source_bundle="$6"
  local expected_error="$7"
  [[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$direct_date' AND revision=$revision;")" == '0' ]] || fail "direct invalid case $label reused owner/date/revision"
  if direct_insert tenant-a "$direct_date" "$run_id" "$revision" "$report_payload" "$source_bundle" > /dev/null 2>"$TEST_TMP/direct-${label}.err"; then
    fail "direct service_role INSERT accepted $label"
  fi
  grep -Fq "violates check constraint \"$expected_error\"" "$TEST_TMP/direct-${label}.err" || fail "direct service_role INSERT hit the wrong constraint for $label"
}

expect_direct_rejected revision_2 '2026-08-11' '20000000-0000-4000-8000-000000000010' 2 \
  '{"reportingDate":"2026-08-11","revision":2,"currency":"JPY","fixture":"synthetic"}' "$BASE_SOURCE" lm_cfo_daily_snapshots_revision_check
expect_direct_rejected report_date_mismatch '2026-08-12' '20000000-0000-4000-8000-000000000011' 1 \
  '{"reportingDate":"2026-08-13","revision":1,"currency":"JPY","fixture":"synthetic"}' "$BASE_SOURCE" lm_cfo_daily_snapshots_report_shape
expect_direct_rejected report_revision_mismatch '2026-08-14' '20000000-0000-4000-8000-000000000012' 1 \
  '{"reportingDate":"2026-08-14","revision":2,"currency":"JPY","fixture":"synthetic"}' "$BASE_SOURCE" lm_cfo_daily_snapshots_report_shape
expect_direct_rejected non_jpy '2026-08-15' '20000000-0000-4000-8000-000000000013' 1 \
  '{"reportingDate":"2026-08-15","revision":1,"currency":"USD","fixture":"synthetic"}' "$BASE_SOURCE" lm_cfo_daily_snapshots_report_shape
expect_direct_rejected wrong_source_identity '2026-08-16' '20000000-0000-4000-8000-000000000014' 1 \
  '{"reportingDate":"2026-08-16","revision":1,"currency":"JPY","fixture":"synthetic"}' \
  '{"source":{"sourceId":"wrong_source"},"state":{"sourceId":"moneytree_mufg"},"fixture":"synthetic"}' lm_cfo_daily_snapshots_source_shape
expect_direct_rejected wrong_state_identity '2026-08-17' '20000000-0000-4000-8000-000000000015' 1 \
  '{"reportingDate":"2026-08-17","revision":1,"currency":"JPY","fixture":"synthetic"}' \
  '{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"wrong_state"},"fixture":"synthetic"}' lm_cfo_daily_snapshots_source_shape
expect_direct_rejected non_object_payload '2026-08-18' '20000000-0000-4000-8000-000000000016' 1 '[]' "$BASE_SOURCE" lm_cfo_daily_snapshots_report_shape
expect_direct_rejected report_revision_string '2026-08-19' '20000000-0000-4000-8000-000000000017' 1 \
  '{"reportingDate":"2026-08-19","revision":"1","currency":"JPY","fixture":"synthetic"}' "$BASE_SOURCE" lm_cfo_daily_snapshots_report_shape
expect_direct_rejected non_object_source_bundle '2026-08-20' '20000000-0000-4000-8000-000000000018' 1 \
  '{"reportingDate":"2026-08-20","revision":1,"currency":"JPY","fixture":"synthetic"}' '[]' lm_cfo_daily_snapshots_source_shape

if "${PSQL[@]}" -c "UPDATE public.lm_cfo_daily_snapshots SET revision=1 WHERE uid='tenant-a' AND reporting_date=DATE '$BASE_DATE';" >/dev/null 2>&1; then
  fail 'superuser UPDATE bypassed append-only trigger'
fi
if "${PSQL[@]}" -c "DELETE FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$BASE_DATE';" >/dev/null 2>&1; then
  fail 'superuser DELETE bypassed append-only trigger'
fi
if "${PSQL[@]}" -c "SET ROLE service_role; UPDATE public.lm_cfo_daily_snapshots SET revision=1 WHERE uid='tenant-a';" >/dev/null 2>&1; then
  fail 'service_role UPDATE was granted'
fi
if "${PSQL[@]}" -c "SET ROLE service_role; DELETE FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a';" >/dev/null 2>&1; then
  fail 'service_role DELETE was granted'
fi

CONCURRENT_DATE='2026-08-10'
CONCURRENT_RUN='20000000-0000-4000-8000-000000000003'
CONCURRENT_REPORT='{"reportingDate":"2026-08-10","revision":1,"currency":"JPY","fixture":"concurrent"}'
SESSION_A="$TEST_TMP/session-a.sql"
SESSION_B="$TEST_TMP/session-b.sql"
SESSION_A_OUT="$TEST_TMP/session-a.out"
SESSION_B_OUT="$TEST_TMP/session-b.out"
CONCURRENT_CALL="SELECT public.lm_append_cfo_daily_snapshot('tenant-a', DATE '$CONCURRENT_DATE', '$CONCURRENT_RUN'::uuid, \$json\$${CONCURRENT_REPORT}\$json\$::jsonb, \$json\$${BASE_SOURCE}\$json\$::jsonb)->>'public_ref';"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$CONCURRENT_CALL" 'SELECT pg_sleep(5);' 'COMMIT;' >"$SESSION_A"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$CONCURRENT_CALL" 'COMMIT;' >"$SESSION_B"

"${PSQL[@]}" -Atqf "$SESSION_A" >"$SESSION_A_OUT" 2>"$TEST_TMP/session-a.err" &
A_PID=$!
WAITING=0
for _ in {1..100}; do
  WAITING="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state='active' AND query LIKE '%pg_sleep(5)%';" | tr -d '[:space:]')"
  [[ "$WAITING" == '1' ]] && break
  sleep 0.1
done
[[ "$WAITING" == '1' ]] || fail 'first concurrent session did not reach its hold point'
"${PSQL[@]}" -Atqf "$SESSION_B" >"$SESSION_B_OUT" 2>"$TEST_TMP/session-b.err" &
B_PID=$!
LOCK_WAITING=0
for _ in {1..100}; do
  LOCK_WAITING="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state='active' AND query LIKE '%lm_append_cfo_daily_snapshot%' AND wait_event_type='Lock';" | tr -d '[:space:]')"
  [[ "$LOCK_WAITING" == '1' ]] && break
  sleep 0.1
done
[[ "$LOCK_WAITING" == '1' ]] || fail 'second concurrent RPC never waited on the first transaction'
wait "$A_PID"
wait "$B_PID"

CONCURRENT_A_REF="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_A_OUT" | head -n 1)"
CONCURRENT_B_REF="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_B_OUT" | head -n 1)"
[[ "$CONCURRENT_A_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'first concurrent session returned no public_ref'
[[ "$CONCURRENT_A_REF" == "$CONCURRENT_B_REF" ]] || fail 'concurrent identical append returned different public_refs'
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$CONCURRENT_DATE' AND run_id='$CONCURRENT_RUN'::uuid;")" == '1' ]] || fail 'concurrent identical append created more than one row'

TENANT_B_RUN='20000000-0000-4000-8000-000000000004'
TENANT_B_REF="$(append_sql tenant-b "$BASE_DATE" "$TENANT_B_RUN" "$BASE_REPORT" "$BASE_SOURCE")"
[[ "$TENANT_B_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'second tenant same-date snapshot was not created'
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-a' AND reporting_date=DATE '$BASE_DATE';")" == '1' ]] || fail 'tenant-a baseline was not isolated'
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='tenant-b' AND reporting_date=DATE '$BASE_DATE' AND revision=1;")" == '1' ]] || fail 'tenant-b same-date revision was not isolated'

printf '%s\n' 'cfo-daily-snapshot-postgres: PASS'
