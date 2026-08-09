#!/usr/bin/env bash
# shellcheck disable=SC2068
set -euo pipefail

export PATH="/opt/homebrew/bin:$PATH"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION_SNAPSHOT="$ROOT_DIR/migrations/2026-08-09-cfo-daily-snapshots.sql"
MIGRATION_CORRECTIONS="$ROOT_DIR/migrations/2026-08-09-cfo-snapshot-corrections.sql"
MIGRATION_HARDENING="$ROOT_DIR/migrations/2026-08-09-cfo-snapshot-privilege-hardening.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/cfo-snapshot-corrections-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="cfo_snapshot_corrections_test"
ISOLATED_DB_NAME="cfo_snapshot_corrections_isolated_$$"
DB_MODE="local"
DOCKER_NAME="cfo-snapshot-corrections-pg-$$"
ISOLATED_DB_READY='0'
DROPDB_ARGS=()

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ "$ISOLATED_DB_READY" == '1' ]]; then
    dropdb "${DROPDB_ARGS[@]}" --if-exists "$ISOLATED_DB_NAME" >/dev/null 2>&1 || true
  fi
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
  DROPDB_ARGS=(-h "$PGSOCKET_DIR")
  createdb -h "$PGSOCKET_DIR" "$ISOLATED_DB_NAME"
  PSQL_ISOLATED=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$ISOLATED_DB_NAME")
  ISOLATED_DB_READY='1'
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
  DROPDB_ARGS=(-h 127.0.0.1 -p "$PGPORT" -U postgres)
  createdb -h 127.0.0.1 -p "$PGPORT" -U postgres "$ISOLATED_DB_NAME"
  PSQL_ISOLATED=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$ISOLATED_DB_NAME")
  ISOLATED_DB_READY='1'
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

"${PSQL_ISOLATED[@]}" >/dev/null <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
SQL

MIGRATION_ERR="$TEST_TMP/migration.err"
PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_SNAPSHOT" >/dev/null 2>"$MIGRATION_ERR" || fail 'snapshot migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "snapshot migration wrote stderr: $(<"$MIGRATION_ERR")"

# Reproduce the Supabase default table overgrant that Task 7b observed.
"${PSQL[@]}" >/dev/null <<'SQL'
GRANT ALL PRIVILEGES ON TABLE public.lm_cfo_daily_snapshots TO service_role;
SQL
for privilege in TRUNCATE REFERENCES TRIGGER MAINTAIN; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', '$privilege');")" == 't' ]] \
    || fail "default service_role overgrant did not include $privilege"
done

expect_error() {
  local label="$1" expected="$2" sql="$3" err="$TEST_TMP/$1.err"
  if "${PSQL[@]}" -c "$sql" >/dev/null 2>"$err"; then
    fail "$label unexpectedly succeeded"
  fi
  grep -Fq "ERROR:  $expected" "$err" || fail "$label returned an unexpected error"
}

constraint_catalog() {
  local -a psql_command=("$@")
  "${psql_command[@]}" -Atqc "
WITH normalized AS (
  SELECT
    c.conname,
    jsonb_build_object(
      'name', c.conname,
      'type', c.contype,
      'validated', c.convalidated,
      'deferrable', c.condeferrable,
      'deferred', c.condeferred,
      'definition', pg_get_constraintdef(c.oid, true),
      'source_columns', c.conkey,
      'target_table', CASE WHEN c.confrelid = 0 THEN NULL ELSE c.confrelid::regclass::text END,
      'target_columns', c.confkey,
      'update_action', c.confupdtype,
      'delete_action', c.confdeltype,
      'match_action', c.confmatchtype
    )::text AS semantics
  FROM pg_constraint AS c
  WHERE c.conrelid = 'public.lm_cfo_daily_snapshots'::regclass
), rows_with_digest AS (
  SELECT conname, encode(digest(semantics, 'sha256'), 'hex') AS digest
  FROM normalized
)
SELECT jsonb_build_object(
  'names', COALESCE((SELECT string_agg(conname, ',' ORDER BY conname) FROM rows_with_digest), ''),
  'digest_prefix', left(encode(digest(COALESCE((SELECT string_agg(conname || ':' || digest, '|' ORDER BY conname) FROM rows_with_digest), ''), 'sha256'), 'hex'), 16)
)::text;
"
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

R1_OLD_SCHEMA_RECEIPT="$(legacy_call owner-a 2026-08-09 "$RUN_1" "$REPORT_1" "$SOURCE_1")"
R1_PRE_COUNT="$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots")"
R1_PRE_ROW="$(${PSQL[@]} -Atqc "SELECT jsonb_build_object('public_ref', public_ref::text, 'uid', uid, 'reporting_date', reporting_date::text, 'run_id', run_id::text, 'revision', revision, 'report_payload', report_payload, 'source_bundle', source_bundle, 'created_at', created_at) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND run_id='$RUN_1'::uuid AND revision=1")"
[[ "$R1_PRE_COUNT" == 1 && -n "$R1_PRE_ROW" ]] || fail 'old-schema revision 1 capture failed'
R1_OLD_SCHEMA_CANON="$(jq -cS . <<<"$R1_OLD_SCHEMA_RECEIPT")"
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R1_OLD_SCHEMA_CANON")" == 'created_at,public_ref,reporting_date,revision,run_id' ]] || fail 'old-schema receipt keys are not exactly five'
[[ "$(jq -er 'has("uid") or has("id") or has("report_payload") or has("source_bundle") or has("supersedes_revision")' <<<"$R1_OLD_SCHEMA_CANON")" == false ]] || fail 'old-schema receipt contains forward/private keys'
[[ "$(jq -er '(.public_ref | type) == "string" and (.reporting_date | type) == "string" and (.run_id | type) == "string" and (.revision | type) == "number" and (.created_at | type) == "string"' <<<"$R1_OLD_SCHEMA_CANON")" == true ]] || fail 'old-schema receipt value types are wrong'
[[ "$(jq -er '.public_ref == $ref and .reporting_date == "2026-08-09" and .run_id == $run and .revision == 1 and .created_at == $created' --arg ref "$(jq -er '.public_ref' <<<"$R1_PRE_ROW")" --arg run "$RUN_1" --arg created "$(jq -er '.created_at' <<<"$R1_PRE_ROW")" <<<"$R1_OLD_SCHEMA_CANON")" == true ]] || fail 'old-schema receipt values do not equal captured revision 1 row'

PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_CORRECTIONS" >/dev/null 2>"$MIGRATION_ERR" || fail 'correction migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "correction migration wrote stderr: $(<"$MIGRATION_ERR")"

for privilege in TRUNCATE REFERENCES TRIGGER MAINTAIN; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', '$privilege');")" == 't' ]] \
    || fail "correction chain unexpectedly removed $privilege"
done

PRIMARY_TEST_CONSTRAINT_CATALOG_BEFORE="$(constraint_catalog "${PSQL[@]}")"

PGOPTIONS='-c client_min_messages=warning' "${PSQL_ISOLATED[@]}" -f "$MIGRATION_SNAPSHOT" >/dev/null 2>"$MIGRATION_ERR" || fail 'isolated snapshot migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "isolated snapshot migration wrote stderr: $(<"$MIGRATION_ERR")"
PGOPTIONS='-c client_min_messages=warning' "${PSQL_ISOLATED[@]}" -f "$MIGRATION_CORRECTIONS" >/dev/null 2>"$MIGRATION_ERR" || fail 'isolated correction migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "isolated correction migration wrote stderr: $(<"$MIGRATION_ERR")"
ISOLATED_CONSTRAINT_CATALOG="$(constraint_catalog "${PSQL_ISOLATED[@]}")"

PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_HARDENING" >/dev/null 2>"$MIGRATION_ERR" || fail 'privilege hardening migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "privilege hardening migration wrote stderr: $(<"$MIGRATION_ERR")"
PGOPTIONS='-c client_min_messages=warning' "${PSQL[@]}" -f "$MIGRATION_HARDENING" >/dev/null 2>"$MIGRATION_ERR" || fail 'privilege hardening migration is not idempotent'
[[ ! -s "$MIGRATION_ERR" ]] || fail "idempotent hardening migration wrote stderr: $(<"$MIGRATION_ERR")"
PGOPTIONS='-c client_min_messages=warning' "${PSQL_ISOLATED[@]}" -f "$MIGRATION_HARDENING" >/dev/null 2>"$MIGRATION_ERR" || fail 'isolated privilege hardening migration failed'
[[ ! -s "$MIGRATION_ERR" ]] || fail "isolated hardening migration wrote stderr: $(<"$MIGRATION_ERR")"

PRIMARY_TEST_CONSTRAINT_CATALOG_AFTER="$(constraint_catalog "${PSQL[@]}")"
PRIMARY_TEST_NAMES="$(jq -er '.names' <<<"$PRIMARY_TEST_CONSTRAINT_CATALOG_AFTER")"
ISOLATED_NAMES="$(jq -er '.names' <<<"$ISOLATED_CONSTRAINT_CATALOG")"
PRIMARY_TEST_BEFORE_NAMES="$(jq -er '.names' <<<"$PRIMARY_TEST_CONSTRAINT_CATALOG_BEFORE")"
PRIMARY_TEST_DIGEST="$(jq -er '.digest_prefix' <<<"$PRIMARY_TEST_CONSTRAINT_CATALOG_AFTER")"
ISOLATED_DIGEST="$(jq -er '.digest_prefix' <<<"$ISOLATED_CONSTRAINT_CATALOG")"
PRIMARY_TEST_BEFORE_DIGEST="$(jq -er '.digest_prefix' <<<"$PRIMARY_TEST_CONSTRAINT_CATALOG_BEFORE")"
CONSTRAINT_NAMES_MATCH='false'
CONSTRAINT_SEMANTICS_MATCH='false'
CONSTRAINT_BEFORE_AFTER_MATCH='false'
[[ "$PRIMARY_TEST_NAMES" == "$ISOLATED_NAMES" ]] && CONSTRAINT_NAMES_MATCH='true'
[[ "$PRIMARY_TEST_BEFORE_NAMES" == "$PRIMARY_TEST_NAMES" && "$PRIMARY_TEST_BEFORE_DIGEST" == "$PRIMARY_TEST_DIGEST" ]] && CONSTRAINT_BEFORE_AFTER_MATCH='true'
[[ "$PRIMARY_TEST_DIGEST" == "$ISOLATED_DIGEST" && "$CONSTRAINT_BEFORE_AFTER_MATCH" == 'true' ]] && CONSTRAINT_SEMANTICS_MATCH='true'
EVIDENCE_DIR="$ROOT_DIR/../../.superpowers/sdd/2026-08-09-life-manager-cfo-moneytree-recovery"
EVIDENCE_PATH="$EVIDENCE_DIR/task-7c-catalog-evidence.json"
mkdir -p "$EVIDENCE_DIR"
jq -cn \
  --arg primaryTestNames "$PRIMARY_TEST_NAMES" \
  --arg isolatedNames "$ISOLATED_NAMES" \
  --arg primaryTestBeforeDigest "$PRIMARY_TEST_BEFORE_DIGEST" \
  --arg primaryTestDigest "$PRIMARY_TEST_DIGEST" \
  --arg isolatedDigest "$ISOLATED_DIGEST" \
  --argjson namesMatch "$CONSTRAINT_NAMES_MATCH" \
  --argjson beforeAfterMatch "$CONSTRAINT_BEFORE_AFTER_MATCH" \
  --argjson semanticsMatch "$CONSTRAINT_SEMANTICS_MATCH" \
  '{primaryTestConstraintNames:$primaryTestNames, isolatedTestConstraintNames:$isolatedNames, constraintNamesMatch:$namesMatch, primaryTestBeforeDigestPrefix:$primaryTestBeforeDigest, primaryTestDigestPrefix:$primaryTestDigest, isolatedTestDigestPrefix:$isolatedDigest, constraintBeforeAfterMatch:$beforeAfterMatch, constraintSemanticsMatch:$semanticsMatch}' >"$EVIDENCE_PATH"
[[ "$CONSTRAINT_SEMANTICS_MATCH" == 'true' ]] || fail 'isolated catalog constraint semantics mismatch'

for privilege in SELECT INSERT; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', '$privilege');")" == 't' ]] \
    || fail "service_role lost required $privilege privilege"
done
for privilege in UPDATE DELETE TRUNCATE REFERENCES TRIGGER MAINTAIN; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_table_privilege('service_role', 'public.lm_cfo_daily_snapshots', '$privilege');")" == 'f' ]] \
    || fail "service_role retained forbidden $privilege privilege"
done
for role in public anon authenticated app_owner; do
  for privilege in SELECT INSERT UPDATE DELETE TRUNCATE REFERENCES TRIGGER MAINTAIN; do
    [[ "$(${PSQL[@]} -Atqc "SELECT has_table_privilege('$role', 'public.lm_cfo_daily_snapshots', '$privilege');")" == 'f' ]] \
      || fail "$role retained table privilege $privilege"
  done
done
for fn in 'public.reject_lm_cfo_daily_snapshot_mutation()' 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)' 'public.lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)'; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_function_privilege('service_role', '$fn', 'EXECUTE') AND NOT has_function_privilege('public', '$fn', 'EXECUTE') AND NOT has_function_privilege('anon', '$fn', 'EXECUTE') AND NOT has_function_privilege('authenticated', '$fn', 'EXECUTE');")" == 't' ]] \
    || fail "RPC EXECUTE ACL changed for $fn"
done
for privilege in USAGE SELECT; do
  [[ "$(${PSQL[@]} -Atqc "SELECT has_sequence_privilege('service_role', 'public.lm_cfo_daily_snapshots_id_seq', '$privilege');")" == 't' ]] \
    || fail "sequence $privilege privilege changed"
done
R1_POST_COUNT="$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots")"
R1_POST_ROW="$(${PSQL[@]} -Atqc "SELECT jsonb_build_object('public_ref', public_ref::text, 'uid', uid, 'reporting_date', reporting_date::text, 'run_id', run_id::text, 'revision', revision, 'report_payload', report_payload, 'source_bundle', source_bundle, 'created_at', created_at, 'supersedes_revision', supersedes_revision) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND run_id='$RUN_1'::uuid AND revision=1")"
[[ "$R1_POST_COUNT" == "$R1_PRE_COUNT" ]] || fail 'correction migration changed row count'
[[ "$(jq -cS 'del(.supersedes_revision)' <<<"$R1_POST_ROW")" == "$(jq -cS . <<<"$R1_PRE_ROW")" ]] || fail 'correction migration changed captured revision 1 facts'
[[ "$(jq -er '.supersedes_revision == null' <<<"$R1_POST_ROW")" == true ]] || fail 'revision 1 supersedes_revision is not null'

R1_RECEIPT="$(legacy_call owner-a 2026-08-09 "$RUN_1" "$REPORT_1" "$SOURCE_1")"
R1_RETRY="$(legacy_call owner-a 2026-08-09 "$RUN_1" "$REPORT_1" "$SOURCE_1")"
R1_RECEIPT_CANON="$(jq -cS . <<<"$R1_RECEIPT")"
R1_RETRY_CANON="$(jq -cS . <<<"$R1_RETRY")"
[[ "$R1_RECEIPT_CANON" == "$R1_RETRY_CANON" ]] || fail 'legacy revision 1 retry changed the receipt'
R1_ROW_RECEIPT="$(${PSQL[@]} -Atqc "SELECT jsonb_build_object('public_ref', public_ref::text, 'reporting_date', reporting_date::text, 'run_id', run_id::text, 'revision', revision, 'supersedes_revision', supersedes_revision, 'created_at', created_at) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND run_id='$RUN_1'::uuid AND revision=1")"
[[ "$R1_RECEIPT_CANON" == "$(jq -cS . <<<"$R1_ROW_RECEIPT")" ]] || fail 'legacy receipt does not equal the complete persisted row receipt'
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R1_RECEIPT_CANON")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'legacy receipt keys are not exactly six'
[[ "$(jq -er '.public_ref == $ref and .reporting_date == "2026-08-09" and .run_id == $run and .revision == 1 and .supersedes_revision == null and (.created_at | type) == "string"' --arg ref "$(jq -er '.public_ref' <<<"$R1_PRE_ROW")" --arg run "$RUN_1" <<<"$R1_RECEIPT_CANON")" == true ]] || fail 'legacy receipt facts or types are wrong'
[[ "$(jq -er 'has("uid") or has("id") or has("report_payload") or has("source_bundle")' <<<"$R1_RECEIPT_CANON")" == false ]] || fail 'legacy receipt contains private keys'

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

# Catalog assertions below verify definitions and ordered columns, not only object names.
"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
DECLARE
  snapshot_oid oid := 'public.lm_cfo_daily_snapshots'::regclass;
  uid_att smallint := (SELECT attnum FROM pg_attribute WHERE attrelid = snapshot_oid AND attname = 'uid');
  date_att smallint := (SELECT attnum FROM pg_attribute WHERE attrelid = snapshot_oid AND attname = 'reporting_date');
  run_att smallint := (SELECT attnum FROM pg_attribute WHERE attrelid = snapshot_oid AND attname = 'run_id');
  revision_att smallint := (SELECT attnum FROM pg_attribute WHERE attrelid = snapshot_oid AND attname = 'revision');
  predecessor_att smallint := (SELECT attnum FROM pg_attribute WHERE attrelid = snapshot_oid AND attname = 'supersedes_revision');
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = snapshot_oid AND contype = 'c' AND convalidated AND pg_get_expr(conbin, conrelid) ~ 'revision > 0') THEN
    RAISE EXCEPTION 'revision positive check definition is missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = snapshot_oid AND contype = 'c' AND convalidated AND pg_get_expr(conbin, conrelid) ~ 'revision = 1' AND pg_get_expr(conbin, conrelid) ~ 'supersedes_revision IS NULL' AND pg_get_expr(conbin, conrelid) ~ 'revision > 1' AND pg_get_expr(conbin, conrelid) ~ 'supersedes_revision = .*revision - 1') THEN
    RAISE EXCEPTION 'predecessor check definition is missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = snapshot_oid AND confrelid = snapshot_oid AND contype = 'f' AND convalidated AND conkey = ARRAY[uid_att, date_att, run_att, predecessor_att]::smallint[] AND confkey = ARRAY[uid_att, date_att, run_att, revision_att]::smallint[]) THEN
    RAISE EXCEPTION 'predecessor self-FK definition is missing';
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

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
DECLARE
  snapshot_oid oid := 'public.lm_cfo_daily_snapshots'::regclass;
BEGIN
  IF (SELECT count(*) FROM pg_index AS i WHERE i.indrelid = snapshot_oid AND i.indisunique AND i.indisvalid AND i.indisready AND (SELECT array_agg(a.attname::text ORDER BY k.ord) FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) JOIN pg_attribute AS a ON a.attrelid = snapshot_oid AND a.attnum = k.attnum) = ARRAY['uid','reporting_date','revision']) <> 1 THEN
    RAISE EXCEPTION 'retained owner/date/revision unique definition is missing';
  END IF;
  IF (SELECT count(*) FROM pg_index AS i WHERE i.indrelid = snapshot_oid AND i.indisunique AND i.indisvalid AND i.indisready AND (SELECT array_agg(a.attname::text ORDER BY k.ord) FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) JOIN pg_attribute AS a ON a.attrelid = snapshot_oid AND a.attnum = k.attnum) = ARRAY['uid','reporting_date','run_id','revision']) <> 1 THEN
    RAISE EXCEPTION 'correction owner/date/run/revision unique definition is missing';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_index AS i WHERE i.indrelid = snapshot_oid AND i.indisunique AND i.indisvalid AND i.indisready AND (SELECT array_agg(a.attname::text ORDER BY k.ord) FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) JOIN pg_attribute AS a ON a.attrelid = snapshot_oid AND a.attnum = k.attnum) = ARRAY['uid','reporting_date','run_id']) THEN
    RAISE EXCEPTION 'legacy owner/date/run unique definition remains';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = snapshot_oid AND NOT tgisinternal AND tgenabled = 'O' AND tgtype = 27 AND tgfoid = 'public.reject_lm_cfo_daily_snapshot_mutation()'::regprocedure AND position('BEFORE DELETE OR UPDATE' IN upper(pg_get_triggerdef(oid))) > 0 AND position('EXECUTE FUNCTION reject_lm_cfo_daily_snapshot_mutation()' IN pg_get_triggerdef(oid)) > 0) THEN
    RAISE EXCEPTION 'append-only trigger definition is missing';
  END IF;
END $$;
SQL

for fn in 'public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb)' 'public.lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)'; do
  [[ "$(${PSQL[@]} -Atqc "SELECT prosecdef AND proconfig=ARRAY['search_path=pg_catalog, public'] AND proacl IS NOT NULL AND NOT EXISTS (SELECT 1 FROM unnest(proacl) AS acl WHERE acl::text LIKE 'anon=%' OR acl::text LIKE 'authenticated=%' OR acl::text LIKE 'PUBLIC=%') AND has_function_privilege('service_role', '$fn', 'EXECUTE') AND NOT has_function_privilege('anon', '$fn', 'EXECUTE') AND NOT has_function_privilege('authenticated', '$fn', 'EXECUTE') FROM pg_proc WHERE oid='$fn'::regprocedure")" == t ]] || fail "RPC security/ACL contract failed for $fn"
done

R2_RECEIPT="$(revision_call owner-a 2026-08-09 "$RUN_1" 2 1 "$REPORT_2" "$SOURCE_2")"
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R2_RECEIPT")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'revision 2 receipt keys are not exactly six'
[[ "$(jq -er '.revision == 2 and .supersedes_revision == 1' <<<"$R2_RECEIPT")" == true ]] || fail 'revision 2 does not link revision 1'
R2_RETRY="$(revision_call owner-a 2026-08-09 "$RUN_1" 2 1 "$REPORT_2" "$SOURCE_2")"
R2_RECEIPT_CANON="$(jq -cS . <<<"$R2_RECEIPT")"
R2_RETRY_CANON="$(jq -cS . <<<"$R2_RETRY")"
[[ "$R2_RECEIPT_CANON" == "$R2_RETRY_CANON" ]] || fail 'identical revision 2 retry changed the complete receipt'
R2_ROW_RECEIPT="$(${PSQL[@]} -Atqc "SELECT jsonb_build_object('public_ref', public_ref::text, 'reporting_date', reporting_date::text, 'run_id', run_id::text, 'revision', revision, 'supersedes_revision', supersedes_revision, 'created_at', created_at) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND run_id='$RUN_1'::uuid AND revision=2")"
[[ "$R2_RECEIPT_CANON" == "$(jq -cS . <<<"$R2_ROW_RECEIPT")" ]] || fail 'revision 2 receipt does not equal the complete persisted row receipt'
[[ "$(jq -er 'keys | sort | join(",")' <<<"$R2_RECEIPT_CANON")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'revision 2 receipt keys are not exactly six'
[[ "$(jq -er '(.public_ref | type) == "string" and (.reporting_date == "2026-08-09") and (.run_id == $run) and (.revision == 2) and (.supersedes_revision == 1) and (.created_at | type) == "string" and (has("uid") | not)' --arg run "$RUN_1" <<<"$R2_RECEIPT_CANON")" == true ]] || fail 'revision 2 receipt facts or types are wrong'
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
CONCURRENT_RECEIPT_A="$(awk '/^\{.*\}$/ {print}' "$OUT_A" | jq -cS .)" || fail 'first concurrent complete receipt missing'
CONCURRENT_RECEIPT_B="$(awk '/^\{.*\}$/ {print}' "$OUT_B" | jq -cS .)" || fail 'second concurrent complete receipt missing'
[[ "$CONCURRENT_RECEIPT_A" == "$CONCURRENT_RECEIPT_B" ]] || fail 'concurrent complete receipts differ'
[[ "$(jq -er 'keys | sort | join(",")' <<<"$CONCURRENT_RECEIPT_A")" == 'created_at,public_ref,reporting_date,revision,run_id,supersedes_revision' ]] || fail 'concurrent receipt keys are not exactly six'
[[ "$(jq -er '(.public_ref | type) == "string" and (.reporting_date == "2026-08-12") and (.run_id == $run) and (.revision == 2) and (.supersedes_revision == 1) and (.created_at | type) == "string" and (has("uid") | not)' --arg run "$CONCURRENT_RUN" <<<"$CONCURRENT_RECEIPT_A")" == true ]] || fail 'concurrent receipt facts or types are wrong'
CONCURRENT_ROW_RECEIPT="$(${PSQL[@]} -Atqc "SELECT jsonb_build_object('public_ref', public_ref::text, 'reporting_date', reporting_date::text, 'run_id', run_id::text, 'revision', revision, 'supersedes_revision', supersedes_revision, 'created_at', created_at) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '$CONCURRENT_DATE' AND run_id='$CONCURRENT_RUN'::uuid AND revision=2")"
[[ "$CONCURRENT_RECEIPT_A" == "$(jq -cS . <<<"$CONCURRENT_ROW_RECEIPT")" ]] || fail 'concurrent receipt does not equal the complete persisted row receipt'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '$CONCURRENT_DATE' AND run_id='$CONCURRENT_RUN'::uuid AND revision=2")" == 1 ]] || fail 'concurrent calls created more than one revision 2 row'

[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_daily_snapshots WHERE uid='owner-a' AND reporting_date=DATE '2026-08-09' AND revision IN (1,2)")" == 2 ]] || fail 'final owner/date row count is not two'
printf '%s\n' 'cfo-snapshot-corrections-postgres: PASS'
