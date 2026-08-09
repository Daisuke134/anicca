#!/usr/bin/env bash
# shellcheck disable=SC2068
set -euo pipefail

export PATH="/opt/homebrew/bin:$PATH"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION_SNAPSHOT="$ROOT_DIR/migrations/2026-08-09-cfo-daily-snapshots.sql"
MIGRATION_CORRECTIONS="$ROOT_DIR/migrations/2026-08-09-cfo-snapshot-corrections.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/cfo-snapshot-corrections-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="cfo_snapshot_corrections_test"
DB_MODE="local"
DOCKER_NAME="cfo-snapshot-corrections-pg-$$"

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

if command -v postgres >/dev/null 2>&1 && command -v initdb >/dev/null 2>&1 && command -v pg_ctl >/dev/null 2>&1; then
  mkdir -p "$PGSOCKET_DIR"
  initdb -D "$PGDATA_DIR" -A trust --no-locale >/dev/null
  pg_ctl -D "$PGDATA_DIR" -l "$PGLOG" -o "-F -h '' -k $PGSOCKET_DIR" start >/dev/null
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$DB_NAME")
  createdb -h "$PGSOCKET_DIR" "$DB_NAME"
  for _ in {1..100}; do
    pg_isready -h "$PGSOCKET_DIR" -d "$DB_NAME" >/dev/null 2>&1 && break
    sleep 0.1
  done
  pg_isready -h "$PGSOCKET_DIR" -d "$DB_NAME" >/dev/null
else
  DB_MODE="docker"
  command -v docker >/dev/null 2>&1 || fail 'PostgreSQL 18 server and Docker are unavailable'
  export PGPASSWORD='cfo-snapshot-corrections-test-only'
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

SERVER_VERSION_NUM="$("${PSQL[@]}" -Atqc 'SHOW server_version_num;')"
[[ "$SERVER_VERSION_NUM" =~ ^18[0-9]{4}$ ]] || fail 'connected server is not PostgreSQL 18'

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE ROLE app_owner NOLOGIN;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('owner-a'), ('owner-b');
SQL

MIGRATION_ERR="$TEST_TMP/migration.err"
PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_SNAPSHOT" >/dev/null 2>"$MIGRATION_ERR" || fail 'snapshot migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "snapshot migration wrote stderr: $(<"$MIGRATION_ERR")"
PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_CORRECTIONS" >/dev/null 2>"$MIGRATION_ERR" || fail 'correction migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "correction migration wrote stderr: $(<"$MIGRATION_ERR")"

expect_error() {
  local label="$1" expected="$2" sql="$3" err="$TEST_TMP/$1.err"
  if "${PSQL[@]}" -c "$sql" >/dev/null 2>"$err"; then
    fail "$label unexpectedly succeeded"
  fi
  grep -Fq "ERROR:  $expected" "$err" || fail "$label returned an unexpected error"
}

REPORT_1='{"reportingDate":"2026-08-09","revision":1,"currency":"JPY","fixture":"r1"}'
SOURCE_1='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"s1"}'
REPORT_2='{"reportingDate":"2026-08-09","revision":2,"currency":"JPY","fixture":"r2"}'
REPORT_1_DATE_10='{"reportingDate":"2026-08-10","revision":1,"currency":"JPY","fixture":"r1-date-10"}'
REPORT_2_DATE_10='{"reportingDate":"2026-08-10","revision":2,"currency":"JPY","fixture":"r2-date-10"}'
REPORT_2_DATE_11='{"reportingDate":"2026-08-11","revision":2,"currency":"JPY","fixture":"r2-date-11"}'
SOURCE_2='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"s2"}'
RUN_1='30000000-0000-4000-8000-000000000001'
RUN_2='30000000-0000-4000-8000-000000000002'
RUN_GAP='30000000-0000-4000-8000-000000000004'

legacy_call() {
  local uid="$1" date="$2" run="$3" report="$4" source="$5"
  "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot('$uid', DATE '$date', '$run'::uuid, \$json\$${report}\$json\$::jsonb, \$json\$${source}\$json\$::jsonb);"
}

revision_call() {
  local uid="$1" date="$2" run="$3" revision="$4" predecessor="$5" report="$6" source="$7"
  "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('$uid', DATE '$date', '$run'::uuid, $revision, $predecessor, \$json\$${report}\$json\$::jsonb, \$json\$${source}\$json\$::jsonb);"
}

R1_RECEIPT="$(legacy_call owner-a 2026-08-09 "$RUN_1" "$REPORT_1" "$SOURCE_1")"
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R1_RECEIPT")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'revision 1 receipt keys are not exactly six'
[[ "$(jq -er 'has("uid") or has("id") or has("report_payload") or has("source_bundle")' <<<"$R1_RECEIPT")" == false ]] || fail 'revision 1 receipt contains private keys'
R1_RETRY="$(legacy_call owner-a 2026-08-09 "$RUN_1" "$REPORT_1" "$SOURCE_1")"
[[ "$(jq -er '.public_ref' <<<"$R1_RECEIPT")" == "$(jq -er '.public_ref' <<<"$R1_RETRY")" ]] || fail 'legacy revision 1 retry changed receipt'

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF (SELECT count(*) FROM public.lm_cfo_daily_snapshots) <> 1 THEN
    RAISE EXCEPTION 'existing revision 1 row did not survive forward migration';
  END IF;
  IF (SELECT revision FROM public.lm_cfo_daily_snapshots) <> 1
     OR (SELECT supersedes_revision FROM public.lm_cfo_daily_snapshots) IS NOT NULL THEN
    RAISE EXCEPTION 'revision 1 row was altered by forward migration';
  END IF;
END $$;
SQL

CATALOG="$(${PSQL[@]} -Atqc "
SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_cfo_daily_snapshots'::regclass
  AND conname IN ('lm_cfo_daily_snapshots_revision_positive','lm_cfo_daily_snapshots_predecessor_contract','lm_cfo_daily_snapshots_owner_date_run_revision_unique','lm_cfo_daily_snapshots_predecessor_fk');")"
[[ "$CATALOG" == 4 ]] || fail 'correction constraints are incomplete'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_cfo_daily_snapshots'::regclass AND conname='lm_cfo_daily_snapshots_predecessor_fk' AND contype='f' AND conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='public.lm_cfo_daily_snapshots'::regclass AND attname='uid'),(SELECT attnum FROM pg_attribute WHERE attrelid='public.lm_cfo_daily_snapshots'::regclass AND attname='reporting_date'),(SELECT attnum FROM pg_attribute WHERE attrelid='public.lm_cfo_daily_snapshots'::regclass AND attname='run_id'),(SELECT attnum FROM pg_attribute WHERE attrelid='public.lm_cfo_daily_snapshots'::regclass AND attname='supersedes_revision')]")" == 1 ]] || fail 'predecessor self-FK columns are wrong'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_cfo_daily_snapshots' AND indexname='lm_cfo_daily_snapshots_owner_date_run_revision_unique'")" == 1 ]] || fail 'revision unique index is missing'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_cfo_daily_snapshots' AND indexname='lm_cfo_daily_snapshots_owner_date_run_unique'")" == 0 ]] || fail 'legacy owner/date/run unique index remains'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_trigger WHERE tgrelid='public.lm_cfo_daily_snapshots'::regclass AND tgname='lm_cfo_daily_snapshots_append_only' AND NOT tgisinternal")" == 1 ]] || fail 'append-only trigger is missing'

for fn in 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)' 'public.lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)'; do
  [[ "$(${PSQL[@]} -Atqc "SELECT prosecdef AND proconfig=ARRAY['search_path=pg_catalog, public'] AND proacl IS NOT NULL AND NOT EXISTS (SELECT 1 FROM unnest(proacl) AS acl WHERE acl::text LIKE 'anon=%' OR acl::text LIKE 'authenticated=%' OR acl::text LIKE 'PUBLIC=%') AND has_function_privilege('service_role', '$fn', 'EXECUTE') AND NOT has_function_privilege('anon', '$fn', 'EXECUTE') AND NOT has_function_privilege('authenticated', '$fn', 'EXECUTE') FROM pg_proc WHERE oid='$fn'::regprocedure")" == t ]] || fail "RPC security/ACL contract failed for $fn"
done

R2_RECEIPT="$(revision_call owner-a 2026-08-09 "$RUN_1" 2 1 "$REPORT_2" "$SOURCE_2")"
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R2_RECEIPT")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'revision 2 receipt keys are not exactly six'
[[ "$(jq -er '.revision == 2 and .supersedes_revision == 1' <<<"$R2_RECEIPT")" == true ]] || fail 'revision 2 does not link revision 1'
R2_RETRY="$(revision_call owner-a 2026-08-09 "$RUN_1" 2 1 "$REPORT_2" "$SOURCE_2")"
[[ "$(jq -er '.public_ref' <<<"$R2_RECEIPT")" == "$(jq -er '.public_ref' <<<"$R2_RETRY")" ]] || fail 'identical revision 2 retry changed receipt'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND run_id='$RUN_1'::uuid")" == 2 ]] || fail 'identical revision 2 retry inserted another row'

CHANGED_REPORT='{"reportingDate":"2026-08-09","revision":2,"currency":"JPY","fixture":"changed"}'
CHANGED_REPORT_SQL="SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-09', '$RUN_1'::uuid, 2, 1, \$json\$${CHANGED_REPORT}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"
expect_error changed_report cfo_snapshot_revision_conflict "$CHANGED_REPORT_SQL"
CHANGED_SOURCE='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"changed-source"}'
CHANGED_SOURCE_SQL="SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-09', '$RUN_1'::uuid, 2, 1, \$json\$${REPORT_2}\$json\$::jsonb, \$json\$${CHANGED_SOURCE}\$json\$::jsonb);"
expect_error changed_source cfo_snapshot_revision_conflict "$CHANGED_SOURCE_SQL"

REPORT_3='{"reportingDate":"2026-08-09","revision":3,"currency":"JPY","fixture":"r3"}'
legacy_call owner-a 2026-08-13 "$RUN_GAP" '{"reportingDate":"2026-08-13","revision":1,"currency":"JPY","fixture":"gap"}' "$SOURCE_1" >/dev/null
REPORT_3_GAP='{"reportingDate":"2026-08-13","revision":3,"currency":"JPY","fixture":"gap-r3"}'
expect_error revision_gap cfo_snapshot_predecessor_missing "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-13', '$RUN_GAP'::uuid, 3, 2, \$json\$${REPORT_3_GAP}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"
expect_error changed_predecessor invalid_snapshot_revision "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-09', '$RUN_1'::uuid, 3, 1, \$json\$${REPORT_3}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"

legacy_call owner-a 2026-08-10 "$RUN_2" "$REPORT_1_DATE_10" "$SOURCE_1" >/dev/null
expect_error cross_owner cfo_snapshot_predecessor_missing "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-b', DATE '2026-08-10', '$RUN_2'::uuid, 2, 1, \$json\$${REPORT_2_DATE_10}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"
expect_error cross_date cfo_snapshot_predecessor_missing "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-11', '$RUN_2'::uuid, 2, 1, \$json\$${REPORT_2_DATE_11}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"
expect_error cross_run cfo_snapshot_predecessor_missing "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-10', '$RUN_1'::uuid, 2, 1, \$json\$${REPORT_2_DATE_10}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"

expect_error superuser_update 'lm_cfo_daily_snapshots is append-only' "UPDATE public.lm_cfo_daily_snapshots SET revision=9 WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09';"
expect_error superuser_delete 'lm_cfo_daily_snapshots is append-only' "DELETE FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09';"
expect_error service_update 'permission denied for table lm_cfo_daily_snapshots' "SET ROLE service_role; UPDATE public.lm_cfo_daily_snapshots SET revision=9 WHERE uid='owner-a';"
expect_error service_delete 'permission denied for table lm_cfo_daily_snapshots' "SET ROLE service_role; DELETE FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a';"
for role in anon authenticated app_owner; do
  expect_error "${role}_update" 'permission denied for table lm_cfo_daily_snapshots' "SET ROLE $role; UPDATE public.lm_cfo_daily_snapshots SET revision=9 WHERE uid='owner-a';"
  expect_error "${role}_delete" 'permission denied for table lm_cfo_daily_snapshots' "SET ROLE $role; DELETE FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a';"
  expect_error "${role}_legacy_rpc" 'permission denied for function lm_append_cfo_daily_snapshot' "SET ROLE $role; SELECT public.lm_append_cfo_daily_snapshot('owner-a', DATE '2026-08-09', '$RUN_1'::uuid, \$json\$${REPORT_1}\$json\$::jsonb, \$json\$${SOURCE_1}\$json\$::jsonb);"
  expect_error "${role}_revision_rpc" 'permission denied for function lm_append_cfo_daily_snapshot_revision' "SET ROLE $role; SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '2026-08-09', '$RUN_1'::uuid, 2, 1, \$json\$${REPORT_2}\$json\$::jsonb, \$json\$${SOURCE_2}\$json\$::jsonb);"
done

CONCURRENT_DATE='2026-08-12'
CONCURRENT_RUN='30000000-0000-4000-8000-000000000003'
CONCURRENT_REPORT='{"reportingDate":"2026-08-12","revision":2,"currency":"JPY","fixture":"concurrent"}'
CONCURRENT_SOURCE='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"concurrent"}'
legacy_call owner-a "$CONCURRENT_DATE" "$CONCURRENT_RUN" '{"reportingDate":"2026-08-12","revision":1,"currency":"JPY","fixture":"concurrent"}' "$CONCURRENT_SOURCE" >/dev/null
SESSION_A="$TEST_TMP/concurrent-a.sql"
SESSION_B="$TEST_TMP/concurrent-b.sql"
OUT_A="$TEST_TMP/concurrent-a.out"
OUT_B="$TEST_TMP/concurrent-b.out"
ERR_A="$TEST_TMP/concurrent-a.err"
ERR_B="$TEST_TMP/concurrent-b.err"
CALL="SELECT public.lm_append_cfo_daily_snapshot_revision('owner-a', DATE '$CONCURRENT_DATE', '$CONCURRENT_RUN'::uuid, 2, 1, \$json\$${CONCURRENT_REPORT}\$json\$::jsonb, \$json\$${CONCURRENT_SOURCE}\$json\$::jsonb);"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$CALL" 'SELECT pg_sleep(2);' 'COMMIT;' >"$SESSION_A"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$CALL" 'COMMIT;' >"$SESSION_B"
PGAPPNAME=cfo-correction-concurrent-a "${PSQL[@]}" -Atqf "$SESSION_A" >"$OUT_A" 2>"$ERR_A" &
PID_A=$!
READY='0'
for _ in {1..100}; do
  [[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_stat_activity WHERE application_name='cfo-correction-concurrent-a' AND query LIKE '%pg_sleep(2)%' AND state='active';" | tr -d '[:space:]')" == '1' ]] && READY='1' && break
  sleep 0.1
done
[[ "$READY" == '1' ]] || fail 'first concurrent correction did not reach its lock barrier'
PGAPPNAME=cfo-correction-concurrent-b "${PSQL[@]}" -Atqf "$SESSION_B" >"$OUT_B" 2>"$ERR_B" &
PID_B=$!
STATUS_A=0
STATUS_B=0
wait "$PID_A" || STATUS_A=$?
wait "$PID_B" || STATUS_B=$?
[[ "$STATUS_A" == 0 && "$STATUS_B" == 0 ]] || fail 'concurrent correction session failed'
[[ ! -s "$ERR_A" && ! -s "$ERR_B" ]] || fail 'concurrent correction wrote stderr'
CONCURRENT_REF_A="$(awk '/^\{.*\}$/ {print}' "$OUT_A" | jq -er '.public_ref')" || fail 'first concurrent receipt missing'
CONCURRENT_REF_B="$(awk '/^\{.*\}$/ {print}' "$OUT_B" | jq -er '.public_ref')" || fail 'second concurrent receipt missing'
[[ "$CONCURRENT_REF_A" == "$CONCURRENT_REF_B" ]] || fail 'concurrent receipts differ'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '$CONCURRENT_DATE' AND run_id='$CONCURRENT_RUN'::uuid AND revision=2")" == 1 ]] || fail 'concurrent calls created more than one revision 2 row'

[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND revision IN (1,2)")" == 2 ]] || fail 'final owner/date row count is not two'
printf '%s\n' 'cfo-snapshot-corrections-postgres: PASS'
