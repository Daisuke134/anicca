#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-07-22-panel-score-outcomes.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/panel-score-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="panel_score_test"
DB_MODE="local"
DOCKER_NAME="panel-score-pg-$$"

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
  export PGPASSWORD="panel-score-test-only"
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
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('tenant-a'), ('tenant-b');
SQL

"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.lm_score_outcomes', 'SELECT')
     OR has_table_privilege('authenticated', 'public.lm_score_outcomes', 'SELECT') THEN
    RAISE EXCEPTION 'browser table grant present';
  END IF;
  IF has_function_privilege('anon', 'public.lm_panel_score_outcome_snapshot(text,jsonb)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.lm_panel_score_outcome_snapshot(text,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser snapshot execute grant present';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_score_outcomes', 'SELECT')
     OR NOT has_function_privilege('service_role', 'public.lm_panel_score_outcome_snapshot(text,jsonb)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service role read contract absent';
  END IF;
END $$;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT public.lm_panel_score_outcome_snapshot('tenant-b', '{}'::jsonb);" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL anon executed snapshot RPC' >&2
  exit 1
fi
if "${PSQL[@]}" -c "SET ROLE authenticated; SELECT count(*) FROM public.lm_score_outcomes;" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL authenticated read outcome table' >&2
  exit 1
fi

append_sql() {
  local payload="$1"
  "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_append_score_outcome(\$json\$$payload\$json\$::jsonb)->>'public_ref';"
}

BASE_PAYLOAD='{"uid":"tenant-a","organ":"daily","entity_key":"event-1","outcome_kind":"daily_call","outcome_status":"required_pending","revision_key":"20000000-0000-4000-8000-000000000001","occurred_at":"2026-07-14T09:00:00.000Z","resolved_at":null,"amount_minor":null,"currency":null,"components":{}}'
FIRST_REF="$(append_sql "$BASE_PAYLOAD")"
RETRY_REF="$(append_sql "$BASE_PAYLOAD")"
[[ "$FIRST_REF" == "$RETRY_REF" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_score_outcomes WHERE uid='tenant-a' AND entity_key='event-1';")" == "1" ]]

ZERO_REVISION_PAYLOAD="${BASE_PAYLOAD/20000000-0000-4000-8000-000000000001/00000000-0000-0000-0000-000000000000}"
if append_sql "$ZERO_REVISION_PAYLOAD" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL zero revision key accepted' >&2
  exit 1
fi

FRACTIONAL_AMOUNT_PAYLOAD='{"uid":"tenant-a","organ":"financial","entity_key":"fractional-amount","outcome_kind":"financial_external_income","outcome_status":"verified","revision_key":"20000000-0000-4000-8000-000000000005","occurred_at":"2026-07-14T09:00:00.000Z","resolved_at":null,"amount_minor":1.5,"currency":"USD","components":{}}'
if append_sql "$FRACTIONAL_AMOUNT_PAYLOAD" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL fractional amount_minor accepted' >&2
  exit 1
fi
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_score_outcomes WHERE uid='tenant-a' AND entity_key='fractional-amount';")" == "0" ]]
if "${PSQL[@]}" -c "SET ROLE service_role; INSERT INTO public.lm_score_outcomes(uid, organ, entity_key, outcome_kind, outcome_status, revision_key, occurred_at, amount_minor, currency, components) VALUES ('tenant-a', 'financial', 'fractional-direct', 'financial_external_income', 'verified', '20000000-0000-4000-8000-000000000006', '2026-07-14T09:00:00.000Z', 1.5, 'USD', '{}'::jsonb);" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL fractional amount_minor bypassed storage check' >&2
  exit 1
fi
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_score_outcomes WHERE uid='tenant-a' AND entity_key='fractional-direct';")" == "0" ]]

CONFLICT_PAYLOAD="${BASE_PAYLOAD/required_pending/required_failed}"
if append_sql "$CONFLICT_PAYLOAD" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL changed payload reused revision key' >&2
  exit 1
fi

CORRECTION_PAYLOAD="${BASE_PAYLOAD/20000000-0000-4000-8000-000000000001/20000000-0000-4000-8000-000000000002}"
append_sql "$CORRECTION_PAYLOAD" >/dev/null
FAILED_PAYLOAD="${BASE_PAYLOAD/required_pending/required_failed}"
FAILED_PAYLOAD="${FAILED_PAYLOAD/20000000-0000-4000-8000-000000000001/20000000-0000-4000-8000-000000000003}"
append_sql "$FAILED_PAYLOAD" >/dev/null
REENTRY_PAYLOAD="${BASE_PAYLOAD/20000000-0000-4000-8000-000000000001/20000000-0000-4000-8000-000000000004}"
append_sql "$REENTRY_PAYLOAD" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_score_outcomes WHERE uid='tenant-a' AND entity_key='event-1';")" == "4" ]]

if "${PSQL[@]}" -c "UPDATE public.lm_score_outcomes SET outcome_status='required_succeeded' WHERE uid='tenant-a';" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only update succeeded' >&2
  exit 1
fi
if "${PSQL[@]}" -c "DELETE FROM public.lm_score_outcomes WHERE uid='tenant-a';" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only delete succeeded' >&2
  exit 1
fi

"${PSQL[@]}" >/dev/null <<'SQL'
SELECT public.lm_append_score_outcome('{"uid":"tenant-a","organ":"physical","entity_key":"need-at-start","outcome_kind":"physical_need","outcome_status":"detected","revision_key":"20000000-0000-4000-8000-000000000010","occurred_at":"2026-06-15T12:00:00.000Z","components":{}}');
SELECT public.lm_append_score_outcome('{"uid":"tenant-a","organ":"mental","entity_key":"trigger-in","outcome_kind":"mental_trigger","outcome_status":"suppression_honored","revision_key":"20000000-0000-4000-8000-000000000011","occurred_at":"2026-07-14T12:00:00.000Z","components":{"send_count":0}}');
SELECT public.lm_append_score_outcome('{"uid":"tenant-a","organ":"financial","entity_key":"income-in","outcome_kind":"financial_external_income","outcome_status":"verified","revision_key":"20000000-0000-4000-8000-000000000012","occurred_at":"2026-07-10T12:00:00.000Z","amount_minor":100,"currency":"USD","components":{}}');
SELECT public.lm_append_score_outcome('{"uid":"tenant-a","organ":"daily","entity_key":"at-end","outcome_kind":"daily_call","outcome_status":"required_succeeded","revision_key":"20000000-0000-4000-8000-000000000013","occurred_at":"2026-07-15T12:00:00.000Z","components":{}}');
SELECT public.lm_append_score_outcome('{"uid":"tenant-b","organ":"daily","entity_key":"other-tenant","outcome_kind":"daily_call","outcome_status":"required_succeeded","revision_key":"20000000-0000-4000-8000-000000000014","occurred_at":"2026-07-14T12:00:00.000Z","components":{}}');
SQL

PERIODS='{"daily":{"start_at":"2026-07-08T12:00:00.000Z","end_at":"2026-07-15T12:00:00.000Z"},"physical":{"start_at":"2026-06-15T12:00:00.000Z","end_at":"2026-07-15T12:00:00.000Z"},"mental":{"start_at":"2026-07-08T12:00:00.000Z","end_at":"2026-07-15T12:00:00.000Z"},"financial":{"start_at":"2026-07-01T00:00:00.000Z","end_at":"2026-07-15T12:00:00.000Z"}}'
FILTER_COUNTS="$("${PSQL[@]}" -Atqc "SET ROLE service_role; WITH s AS (SELECT public.lm_panel_score_outcome_snapshot('tenant-a', \$json\$$PERIODS\$json\$::jsonb) AS v) SELECT jsonb_array_length(v->'rows_by_organ'->'daily')||','||jsonb_array_length(v->'rows_by_organ'->'physical')||','||jsonb_array_length(v->'rows_by_organ'->'mental')||','||jsonb_array_length(v->'rows_by_organ'->'financial') FROM s;")"
[[ "$FILTER_COUNTS" == "4,1,1,1" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE FUNCTION public.panel_score_test_snapshot_gate() RETURNS boolean
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
  PERFORM pg_advisory_lock(88008);
  RETURN true;
END $$;
DROP POLICY lm_score_outcomes_service_select ON public.lm_score_outcomes;
CREATE POLICY lm_score_outcomes_service_select ON public.lm_score_outcomes FOR SELECT TO service_role USING (public.panel_score_test_snapshot_gate());
SQL

SESSION_B="$TEST_TMP/session-b.sql"
SESSION_A_OUT="$TEST_TMP/session-a.out"
printf '%s\n' \
  'SELECT pg_advisory_lock(88008);' \
  'SELECT pg_sleep(5);' \
  "SET ROLE service_role; SELECT public.lm_append_score_outcome('{\"uid\":\"tenant-a\",\"organ\":\"daily\",\"entity_key\":\"concurrent\",\"outcome_kind\":\"daily_call\",\"outcome_status\":\"required_succeeded\",\"revision_key\":\"20000000-0000-4000-8000-000000000099\",\"occurred_at\":\"2026-07-14T12:00:00.000Z\",\"components\":{}}');" \
  'RESET ROLE;' \
  'SELECT pg_advisory_unlock(88008);' >"$SESSION_B"
"${PSQL[@]}" -f "$SESSION_B" >/dev/null &
B_PID=$!
for _ in {1..50}; do
  [[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND objid=88008 AND granted;")" == "1" ]] && break
  sleep 0.1
done
"${PSQL[@]}" -Atqc "SET ROLE service_role; WITH s AS (SELECT public.lm_panel_score_outcome_snapshot('tenant-a', \$json\$$PERIODS\$json\$::jsonb) AS v) SELECT jsonb_array_length(v->'rows_by_organ'->'daily') FROM s;" >"$SESSION_A_OUT" &
A_PID=$!
for _ in {1..40}; do
  WAITING="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND wait_event='advisory' AND query LIKE '%lm_panel_score_outcome_snapshot%';")"
  [[ "$WAITING" != "0" ]] && break
  sleep 0.1
done
[[ "${WAITING:-0}" != "0" ]]
wait "$B_PID"
wait "$A_PID"
[[ "$(tr -d '[:space:]' <"$SESSION_A_OUT")" == "4" ]]
[[ "$("${PSQL[@]}" -Atqc "SET ROLE service_role; WITH s AS (SELECT public.lm_panel_score_outcome_snapshot('tenant-a', \$json\$$PERIODS\$json\$::jsonb) AS v) SELECT jsonb_array_length(v->'rows_by_organ'->'daily') FROM s;")" == "5" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
DROP POLICY lm_score_outcomes_service_select ON public.lm_score_outcomes;
CREATE POLICY lm_score_outcomes_service_select ON public.lm_score_outcomes FOR SELECT TO service_role USING (true);
DROP FUNCTION public.panel_score_test_snapshot_gate();
TRUNCATE public.lm_score_outcomes;
INSERT INTO public.lm_score_outcomes(public_ref, uid, organ, entity_key, outcome_kind, outcome_status, revision_key, occurred_at, components)
SELECT gen_random_uuid(), 'tenant-a', 'daily', 'bulk-' || n, 'daily_call', 'required_succeeded', gen_random_uuid(), '2026-07-14T12:00:00Z', '{}'::jsonb
FROM generate_series(1, 20000) AS n;
SQL

COMPLETE="$("${PSQL[@]}" -Atqc "SET ROLE service_role; WITH s AS (SELECT public.lm_panel_score_outcome_snapshot('tenant-a', \$json\$$PERIODS\$json\$::jsonb) AS v) SELECT (v->>'overflow')||','||jsonb_array_length(v->'rows_by_organ'->'daily') FROM s;")"
[[ "$COMPLETE" == "false,20000" ]]
"${PSQL[@]}" -c "INSERT INTO public.lm_score_outcomes(public_ref, uid, organ, entity_key, outcome_kind, outcome_status, revision_key, occurred_at, components) VALUES (gen_random_uuid(), 'tenant-a', 'daily', 'bulk-20001', 'daily_call', 'required_succeeded', gen_random_uuid(), '2026-07-14T12:00:00Z', '{}'::jsonb);" >/dev/null
OVERFLOW="$("${PSQL[@]}" -Atqc "SET ROLE service_role; WITH s AS (SELECT public.lm_panel_score_outcome_snapshot('tenant-a', \$json\$$PERIODS\$json\$::jsonb) AS v) SELECT (v->>'overflow')||','||(v->'rows_by_organ' = '{}'::jsonb) FROM s;")"
[[ "$OVERFLOW" == "true,true" ]]

printf '%s\n' 'panel-score-postgres: PASS roles=3 snapshot_sessions=2 complete_rows=20000 overflow_rows=20001'
