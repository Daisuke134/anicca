#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION_SNAPSHOT="$ROOT_DIR/migrations/2026-08-09-cfo-daily-snapshots.sql"
MIGRATION_RUN="$ROOT_DIR/migrations/2026-08-09-cfo-daily-runs.sql"
MIGRATION_DELIVERY="$ROOT_DIR/migrations/2026-08-09-cfo-telegram-deliveries.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/cfo-reliable-run-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="cfo_reliable_run_test"
DB_MODE="local"
DOCKER_NAME="cfo-reliable-run-pg-$$"
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
  export PGPASSWORD="cfo-reliable-run-test-only"
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

expect_sql_error() {
  local label="$1" expected="$2" sql="$3"
  local err="$TEST_TMP/${label}.err"
  if "${PSQL[@]}" -c "$sql" >/dev/null 2>"$err"; then
    fail "$label unexpectedly succeeded"
  fi
  grep -Fq "$expected" "$err" || fail "$label returned an unexpected error: $(cat "$err")"
}

# Bootstrap roles and the same lm_users/lm_panel_preferences shape the
# migrations depend on, then apply the full CFO-1g2 migration chain in the
# order Task 6 will apply it live.
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
GRANT SELECT, UPDATE ON TABLE public.lm_panel_preferences TO service_role;
SQL

for migration in "$MIGRATION_SNAPSHOT" "$MIGRATION_RUN" "$MIGRATION_DELIVERY"; do
  "${PSQL[@]}" -f "$migration" >/dev/null
done

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_users(uid) VALUES ('tenant-a'), ('tenant-b'), ('tenant-cross'), ('tenant-run-concurrent');
INSERT INTO public.lm_panel_preferences(uid, call_time_zone) VALUES
  ('tenant-a', 'Asia/Tokyo'), ('tenant-b', 'Asia/Tokyo'),
  ('tenant-cross', 'Asia/Tokyo'), ('tenant-run-concurrent', 'Asia/Tokyo');
SQL

# The public claim RPC must take no clock argument; the database's own time
# is the only source of "now".
CLAIM_RUN_ARGS="$(${PSQL[@]} -Atqc "SELECT pg_get_function_identity_arguments('public.lm_claim_cfo_daily_run'::regproc);")"
[[ "$CLAIM_RUN_ARGS" == 'p_uid text' ]] || fail 'lm_claim_cfo_daily_run must take only p_uid text, no clock parameter'

# Superuser-only calls to the private date helper prove DST and date-boundary
# correctness; application roles must never reach it (revoked from all).
assert_helper_date() {
  local label="$1" tz="$2" instant="$3" expected="$4"
  local actual
  actual="$(${PSQL[@]} -Atqc "SELECT public.lm_cfo_owner_local_date('$tz', '$instant'::timestamptz);")"
  [[ "$actual" == "$expected" ]] || fail "$label expected $expected but got $actual"
}
assert_helper_date dst_spring_forward_before 'America/New_York' '2026-03-08 06:59:59+00' '2026-03-08'
assert_helper_date dst_spring_forward_after  'America/New_York' '2026-03-08 07:00:01+00' '2026-03-08'
assert_helper_date dst_fall_back_before      'America/New_York' '2026-11-01 05:59:59+00' '2026-11-01'
assert_helper_date dst_fall_back_after       'America/New_York' '2026-11-01 06:00:01+00' '2026-11-01'
assert_helper_date date_boundary_before_midnight 'Asia/Tokyo' '2026-08-09 14:59:59+00' '2026-08-09'
assert_helper_date date_boundary_after_midnight  'Asia/Tokyo' '2026-08-09 15:00:01+00' '2026-08-10'

for role in anon authenticated service_role; do
  expect_sql_error "helper_denied_${role}" 'permission denied for function lm_cfo_owner_local_date' \
    "SET ROLE ${role}; SELECT public.lm_cfo_owner_local_date('Asia/Tokyo', statement_timestamp());"
done

# Daily-run permission surface, re-verified against the real migration chain
# (not the synthetic table Task 1b used).
"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.lm_cfo_daily_runs', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_cfo_daily_runs', 'SELECT') THEN
    RAISE EXCEPTION 'browser run-table SELECT grant present';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'INSERT')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'UPDATE')
     OR has_table_privilege('service_role', 'public.lm_cfo_daily_runs', 'DELETE') THEN
    RAISE EXCEPTION 'service-role run-table grants are not append-only';
  END IF;
END $$;
SQL
expect_sql_error run_claim_denied_anon 'permission denied for function lm_claim_cfo_daily_run' \
  "SET ROLE anon; SELECT public.lm_claim_cfo_daily_run('tenant-a');"
expect_sql_error run_claim_denied_authenticated 'permission denied for function lm_claim_cfo_daily_run' \
  "SET ROLE authenticated; SELECT public.lm_claim_cfo_daily_run('tenant-a');"

# Claim a real daily run and append a real snapshot for two tenants so the
# delivery ledger's composite FK has genuine rows to link against.
RUN_A_ID="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-a')->>'run_id';")"
DATE_A="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-a')->>'reporting_date';")"
[[ "$RUN_A_ID" =~ ^[0-9a-f-]{36}$ ]] || fail 'tenant-a daily run claim did not return a run_id'

# Superuser UPDATE/DELETE reach the append-only trigger now that a real row
# exists for tenant-a (an UPDATE/DELETE matching zero rows never fires the
# per-row trigger, so this must run after the claim above).
expect_sql_error runs_update_rejected 'lm_cfo_daily_runs is append-only' \
  "UPDATE public.lm_cfo_daily_runs SET time_zone = time_zone WHERE uid = 'tenant-a';"
expect_sql_error runs_delete_rejected 'lm_cfo_daily_runs is append-only' \
  "DELETE FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-a';"

# The claim RPC uses only database time; the owner-local date it derives must
# match what the (superuser-only) helper computes right now for the same tz.
EXPECTED_TODAY="$(${PSQL[@]} -Atqc "SELECT public.lm_cfo_owner_local_date('Asia/Tokyo', clock_timestamp());")"
[[ "$DATE_A" == "$EXPECTED_TODAY" ]] || fail 'daily run claim reporting_date did not match database-derived owner-local today'

BASE_REPORT_A=$(printf '{"reportingDate":"%s","revision":1,"currency":"JPY","fixture":"reliable-run-a"}' "$DATE_A")
BASE_SOURCE='{"source":{"sourceId":"moneytree_mufg"},"state":{"sourceId":"moneytree_mufg"},"fixture":"reliable-run"}'
SNAPSHOT_A_REF="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot('tenant-a', DATE '$DATE_A', '$RUN_A_ID'::uuid, \$json\$${BASE_REPORT_A}\$json\$::jsonb, \$json\$${BASE_SOURCE}\$json\$::jsonb)->>'public_ref';")"
[[ "$SNAPSHOT_A_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'tenant-a snapshot append did not return a public_ref'

RUN_B_ID="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-b')->>'run_id';")"
DATE_B="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_daily_run('tenant-b')->>'reporting_date';")"
BASE_REPORT_B=$(printf '{"reportingDate":"%s","revision":1,"currency":"JPY","fixture":"reliable-run-b"}' "$DATE_B")
SNAPSHOT_B_REF="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_append_cfo_daily_snapshot('tenant-b', DATE '$DATE_B', '$RUN_B_ID'::uuid, \$json\$${BASE_REPORT_B}\$json\$::jsonb, \$json\$${BASE_SOURCE}\$json\$::jsonb)->>'public_ref';")"
[[ "$SNAPSHOT_B_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'tenant-b snapshot append did not return a public_ref'

OTHER_DATE="$(${PSQL[@]} -Atqc "SELECT (DATE '$DATE_A' + INTERVAL '1 day')::date;")"

# Concurrent claims for the *same* owner/date must serialize to one row/run,
# proven against the real migration chain (mirrors Task 1b's synthetic proof).
SESSION_A="$TEST_TMP/run-session-a.sql"
SESSION_B="$TEST_TMP/run-session-b.sql"
SESSION_A_OUT="$TEST_TMP/run-session-a.out"
SESSION_B_OUT="$TEST_TMP/run-session-b.out"
printf '%s\n' \
  'BEGIN;' \
  'SET ROLE service_role;' \
  "SELECT public.lm_claim_cfo_daily_run('tenant-run-concurrent')->>'run_id';" \
  'SELECT pg_sleep(4);' \
  'COMMIT;' >"$SESSION_A"
printf '%s\n' \
  'BEGIN;' \
  'SET ROLE service_role;' \
  "SELECT public.lm_claim_cfo_daily_run('tenant-run-concurrent')->>'run_id';" \
  'COMMIT;' >"$SESSION_B"

"${PSQL[@]}" -Atqf "$SESSION_A" >"$SESSION_A_OUT" 2>"$TEST_TMP/run-session-a.err" &
A_PID=$!
HOLDING='0'
for _ in {1..100}; do
  HOLDING="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND query LIKE '%pg_sleep(4)%';" | tr -d '[:space:]')"
  [[ "$HOLDING" == '1' ]] && break
  sleep 0.1
done
[[ "$HOLDING" == '1' ]] || fail 'first concurrent run claim did not reach its hold point'

"${PSQL[@]}" -Atqf "$SESSION_B" >"$SESSION_B_OUT" 2>"$TEST_TMP/run-session-b.err" &
B_PID=$!
LOCK_WAITING='0'
for _ in {1..100}; do
  LOCK_WAITING="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND wait_event_type = 'Lock' AND query LIKE '%lm_claim_cfo_daily_run%';" | tr -d '[:space:]')"
  [[ "$LOCK_WAITING" != '0' ]] && break
  sleep 0.1
done
[[ "$LOCK_WAITING" != '0' ]] || fail 'second concurrent run claim never waited on the first transaction'

A_STATUS=0
B_STATUS=0
wait "$A_PID" || A_STATUS=$?
wait "$B_PID" || B_STATUS=$?
A_PID=''
B_PID=''
[[ "$A_STATUS" == '0' && "$B_STATUS" == '0' ]] || fail 'concurrent run claim session failed'
RUN_CONCURRENT_A="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_A_OUT" | head -n 1)"
RUN_CONCURRENT_B="$(sed -n -E 's/^([0-9a-f-]{36})$/\1/p' "$SESSION_B_OUT" | head -n 1)"
[[ "$RUN_CONCURRENT_A" =~ ^[0-9a-f-]{36}$ ]] || fail 'first concurrent run claim returned no run_id'
[[ "$RUN_CONCURRENT_A" == "$RUN_CONCURRENT_B" ]] || fail 'concurrent run claims returned different run IDs'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) || '|' || count(DISTINCT run_id) FROM public.lm_cfo_daily_runs WHERE uid = 'tenant-run-concurrent';")" == '1|1' ]] \
  || fail 'concurrent run claims created more than one row or run'

# Cross-tenant, cross-date, and cross-revision delivery claims must all fail
# the composite snapshot FK; none may create a partial row.
DELIVERY_KIND='daily_report'
DELIVERY_REVISION=1
expect_sql_error cross_tenant_delivery_rejected 'violates foreign key constraint "lm_cfo_telegram_delivery_claims_snapshot_fk"' \
  "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-cross', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION);"
expect_sql_error cross_date_delivery_rejected 'violates foreign key constraint "lm_cfo_telegram_delivery_claims_snapshot_fk"' \
  "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$OTHER_DATE', $DELIVERY_REVISION);"
expect_sql_error cross_revision_delivery_rejected 'violates foreign key constraint "lm_cfo_telegram_delivery_claims_snapshot_fk"' \
  "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', 2);"
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_telegram_delivery_claims;")" == '0' ]] \
  || fail 'a rejected composite linkage left a partial delivery claim row behind'

# Direct invalid rows (bypassing the RPCs) must fail their check constraints.
expect_sql_error direct_invalid_claim_revision 'violates check constraint "lm_cfo_telegram_delivery_claims_revision_check"' \
  "SET ROLE service_role; INSERT INTO public.lm_cfo_telegram_delivery_claims (uid, report_kind, reporting_date, revision, snapshot_public_ref) VALUES ('tenant-a', '$DELIVERY_KIND', DATE '$DATE_A', 0, '$SNAPSHOT_A_REF'::uuid);"
expect_sql_error direct_invalid_receipt_message_id 'violates check constraint "lm_cfo_telegram_delivery_receipts_message_id_check"' \
  "SET ROLE service_role; INSERT INTO public.lm_cfo_telegram_delivery_receipts (claim_public_ref, message_id) VALUES ('$SNAPSHOT_A_REF'::uuid, 0);"

# Concurrent claims for the *same* delivery identity must yield exactly one
# send and one reconcile, with exactly one row created.
DELIVERY_SESSION_A="$TEST_TMP/delivery-session-a.sql"
DELIVERY_SESSION_B="$TEST_TMP/delivery-session-b.sql"
DELIVERY_SESSION_A_OUT="$TEST_TMP/delivery-session-a.out"
DELIVERY_SESSION_B_OUT="$TEST_TMP/delivery-session-b.out"
DELIVERY_CLAIM_CALL="SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION)->>'decision';"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$DELIVERY_CLAIM_CALL" 'SELECT pg_sleep(4);' 'COMMIT;' >"$DELIVERY_SESSION_A"
printf '%s\n' 'BEGIN;' 'SET ROLE service_role;' "$DELIVERY_CLAIM_CALL" 'COMMIT;' >"$DELIVERY_SESSION_B"

"${PSQL[@]}" -Atqf "$DELIVERY_SESSION_A" >"$DELIVERY_SESSION_A_OUT" 2>"$TEST_TMP/delivery-session-a.err" &
A_PID=$!
HOLDING='0'
for _ in {1..100}; do
  HOLDING="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND query LIKE '%pg_sleep(4)%';" | tr -d '[:space:]')"
  [[ "$HOLDING" == '1' ]] && break
  sleep 0.1
done
[[ "$HOLDING" == '1' ]] || fail 'first concurrent delivery claim did not reach its hold point'

"${PSQL[@]}" -Atqf "$DELIVERY_SESSION_B" >"$DELIVERY_SESSION_B_OUT" 2>"$TEST_TMP/delivery-session-b.err" &
B_PID=$!
LOCK_WAITING='0'
for _ in {1..100}; do
  LOCK_WAITING="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND wait_event_type = 'Lock' AND query LIKE '%lm_claim_cfo_telegram_delivery%';" | tr -d '[:space:]')"
  [[ "$LOCK_WAITING" != '0' ]] && break
  sleep 0.1
done
[[ "$LOCK_WAITING" != '0' ]] || fail 'second concurrent delivery claim never waited on the first transaction'

A_STATUS=0
B_STATUS=0
wait "$A_PID" || A_STATUS=$?
wait "$B_PID" || B_STATUS=$?
A_PID=''
B_PID=''
[[ "$A_STATUS" == '0' && "$B_STATUS" == '0' ]] || fail 'concurrent delivery claim session failed'
DECISION_A="$(sed -n -E 's/^(send|sent|reconcile)$/\1/p' "$DELIVERY_SESSION_A_OUT" | head -n 1)"
DECISION_B="$(sed -n -E 's/^(send|sent|reconcile)$/\1/p' "$DELIVERY_SESSION_B_OUT" | head -n 1)"
SEND_COUNT=0
[[ "$DECISION_A" == 'send' ]] && SEND_COUNT=$((SEND_COUNT + 1))
[[ "$DECISION_B" == 'send' ]] && SEND_COUNT=$((SEND_COUNT + 1))
[[ "$SEND_COUNT" == '1' ]] || fail 'concurrent delivery claims did not yield exactly one send'
OTHER_DECISION="$DECISION_A"
[[ "$DECISION_A" == 'send' ]] && OTHER_DECISION="$DECISION_B"
[[ "$OTHER_DECISION" == 'reconcile' ]] || fail 'the losing concurrent delivery claim was not reconcile'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_telegram_delivery_claims WHERE uid = 'tenant-a' AND report_kind = '$DELIVERY_KIND' AND reporting_date = DATE '$DATE_A' AND revision = $DELIVERY_REVISION;")" == '1' ]] \
  || fail 'concurrent delivery claims created more than one row'

CLAIM_A_REF="$(${PSQL[@]} -Atqc "SELECT public_ref FROM public.lm_cfo_telegram_delivery_claims WHERE uid = 'tenant-a' AND report_kind = '$DELIVERY_KIND' AND reporting_date = DATE '$DATE_A' AND revision = $DELIVERY_REVISION;")"
[[ "$CLAIM_A_REF" =~ ^[0-9a-f-]{36}$ ]] || fail 'delivery claim row has no public_ref'

# Unreceipted retry stays reconcile until a provider receipt exists.
RETRY_DECISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION)->>'decision';")"
[[ "$RETRY_DECISION" == 'reconcile' ]] || fail 'unreceipted retry did not return reconcile'

MESSAGE_ID=5551001
RECORD_INITIAL_JSON="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_record_cfo_telegram_delivery('$CLAIM_A_REF'::uuid, $MESSAGE_ID);")"
[[ "$RECORD_INITIAL_JSON" == *"\"message_id\": $MESSAGE_ID"* ]] || fail 'record RPC did not persist the provider message id'

# A receipt makes the next claim retry come back sent.
SENT_DECISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION)->>'decision';")"
[[ "$SENT_DECISION" == 'sent' ]] || fail 'retry after receipt did not return sent'

# The exact same receipt retried is idempotent; a changed message id conflicts.
RECORD_RETRY_JSON="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_record_cfo_telegram_delivery('$CLAIM_A_REF'::uuid, $MESSAGE_ID);")"
[[ "$RECORD_INITIAL_JSON" == "$RECORD_RETRY_JSON" ]] || fail 'exact receipt retry returned a different receipt'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_telegram_delivery_receipts WHERE claim_public_ref = '$CLAIM_A_REF'::uuid;")" == '1' ]] \
  || fail 'exact receipt retry created a duplicate row'
expect_sql_error changed_message_id_conflict 'provider_receipt_conflict' \
  "SET ROLE service_role; SELECT public.lm_record_cfo_telegram_delivery('$CLAIM_A_REF'::uuid, $((MESSAGE_ID + 1)));"

# Role denials and RLS for the delivery ledger.
"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.lm_cfo_telegram_delivery_claims', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_cfo_telegram_delivery_claims', 'SELECT')
     OR has_table_privilege('anon', 'public.lm_cfo_telegram_delivery_receipts', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_cfo_telegram_delivery_receipts', 'SELECT') THEN
    RAISE EXCEPTION 'browser delivery table SELECT grant present';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_claims', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_claims', 'INSERT')
     OR has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_claims', 'UPDATE')
     OR has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_claims', 'DELETE')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_receipts', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_receipts', 'INSERT')
     OR has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_receipts', 'UPDATE')
     OR has_table_privilege('service_role', 'public.lm_cfo_telegram_delivery_receipts', 'DELETE') THEN
    RAISE EXCEPTION 'service-role delivery table grants are not append-only';
  END IF;
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lm_cfo_telegram_delivery_claims'::regclass)
     OR NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.lm_cfo_telegram_delivery_receipts'::regclass) THEN
    RAISE EXCEPTION 'delivery table RLS is disabled';
  END IF;
  IF has_function_privilege('anon', 'public.lm_claim_cfo_telegram_delivery(text,uuid,text,date,integer)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_claim_cfo_telegram_delivery(text,uuid,text,date,integer)', 'EXECUTE')
     OR has_function_privilege('anon', 'public.lm_record_cfo_telegram_delivery(uuid,bigint)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_record_cfo_telegram_delivery(uuid,bigint)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser delivery RPC EXECUTE grant present';
  END IF;
  IF NOT has_function_privilege('service_role', 'public.lm_claim_cfo_telegram_delivery(text,uuid,text,date,integer)', 'EXECUTE')
     OR NOT has_function_privilege('service_role', 'public.lm_record_cfo_telegram_delivery(uuid,bigint)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service-role delivery RPC EXECUTE grant absent';
  END IF;
END $$;
SQL
for role in anon authenticated; do
  expect_sql_error "delivery_claim_denied_${role}" 'permission denied for function lm_claim_cfo_telegram_delivery' \
    "SET ROLE ${role}; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION);"
  expect_sql_error "delivery_record_denied_${role}" 'permission denied for function lm_record_cfo_telegram_delivery' \
    "SET ROLE ${role}; SELECT public.lm_record_cfo_telegram_delivery('$CLAIM_A_REF'::uuid, $MESSAGE_ID);"
done

# Superuser UPDATE/DELETE reach the append-only trigger on both ledger tables.
expect_sql_error delivery_claims_update_rejected 'lm_cfo_telegram_delivery is append-only' \
  "UPDATE public.lm_cfo_telegram_delivery_claims SET revision = revision WHERE uid = 'tenant-a';"
expect_sql_error delivery_claims_delete_rejected 'lm_cfo_telegram_delivery is append-only' \
  "DELETE FROM public.lm_cfo_telegram_delivery_claims WHERE uid = 'tenant-a';"
expect_sql_error delivery_receipts_update_rejected 'lm_cfo_telegram_delivery is append-only' \
  "UPDATE public.lm_cfo_telegram_delivery_receipts SET message_id = message_id WHERE claim_public_ref = '$CLAIM_A_REF'::uuid;"
expect_sql_error delivery_receipts_delete_rejected 'lm_cfo_telegram_delivery is append-only' \
  "DELETE FROM public.lm_cfo_telegram_delivery_receipts WHERE claim_public_ref = '$CLAIM_A_REF'::uuid;"

# Tenant separation: tenant-b's own snapshot/date claims independently and
# does not disturb tenant-a's already-sent delivery.
TENANT_B_DECISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-b', '$SNAPSHOT_B_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_B', $DELIVERY_REVISION)->>'decision';")"
[[ "$TENANT_B_DECISION" == 'send' ]] || fail 'tenant-b fresh delivery claim was not send'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_telegram_delivery_claims WHERE uid = 'tenant-a';")" == '1' ]] \
  || fail 'tenant-a delivery claims were not isolated from tenant-b'
[[ "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_cfo_telegram_delivery_claims WHERE uid = 'tenant-b';")" == '1' ]] \
  || fail 'tenant-b delivery claim was not created'
TENANT_A_STILL_SENT="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.lm_claim_cfo_telegram_delivery('tenant-a', '$SNAPSHOT_A_REF'::uuid, '$DELIVERY_KIND', DATE '$DATE_A', $DELIVERY_REVISION)->>'decision';")"
[[ "$TENANT_A_STILL_SENT" == 'sent' ]] || fail 'tenant-b activity disturbed tenant-a delivery state'

printf '%s\n' 'cfo-reliable-run-postgres: PASS'
