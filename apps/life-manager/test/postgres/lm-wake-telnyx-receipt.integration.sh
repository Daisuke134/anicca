#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-29-lm-wake-telnyx-receipt.sql"
if [[ ! -f "$MIGRATION" ]]; then
  printf '%s\n' 'missing Telnyx receipt migration' >&2
  exit 1
fi

TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-wake-telnyx-receipt-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="lm_wake_telnyx_receipt_test"
DB_MODE="local"
DOCKER_NAME="lm-wake-telnyx-receipt-pg-$$"

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
  export PGPASSWORD="lm-wake-telnyx-receipt-test-only"
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
CREATE TABLE public.lm_wake_log (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  uid text NOT NULL,
  event_key text NOT NULL,
  claim_token text,
  called_at timestamptz,
  answered_at timestamptz,
  amd_result text,
  UNIQUE (uid, event_key),
  CONSTRAINT lm_wake_log_event_key_nonempty CHECK (event_key <> '')
);
ALTER TABLE public.lm_wake_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY lm_wake_log_service_only ON public.lm_wake_log
  USING (current_user = 'service_role') WITH CHECK (current_user = 'service_role');
SQL

"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_wake_log(uid, event_key, claim_token, called_at, answered_at)
VALUES
  ('tenant-a', 'event-a', 'claim-a', '2026-08-29T00:00:00Z', '2026-08-29T00:01:00Z'),
  ('tenant-a', 'event-b', 'claim-b', '2026-08-29T00:00:00Z', NULL),
  ('tenant-b', 'event-a', 'claim-other', '2026-08-29T00:00:00Z', NULL);
SQL

FIRST="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a');")"
[[ "$FIRST" == "1" ]]
LATCH="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id IS NULL, called_at::text, answered_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
[[ "$LATCH" == $'ccid-a|t|2026-08-29 00:00:00+00|2026-08-29 00:01:00+00' ]]

SECOND="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'machine');")"
[[ "$SECOND" == "1" ]]
ENRICHED="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id, telnyx_call_leg_id, telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at IS NOT NULL FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
[[ "$ENRICHED" == $'ccid-a|session-a|leg-a|webhook-a|machine|t' ]]
RECEIVED_AT="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_received_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"

REPLAY="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'human');")"
[[ "$REPLAY" == "1" ]]
REPLAY_CHECK="$(${PSQL[@]} -Atqc "SELECT amd_result, telnyx_webhook_received_at::text = '$RECEIVED_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
[[ "$REPLAY_CHECK" == $'machine|t' ]]

for QUERY in \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-other', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-b', 'event-a', 'claim-other', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-other')"; do
  MATCHED="$(${PSQL[@]} -Atqc "SET ROLE service_role; $QUERY;")"
  [[ "$MATCHED" == "0" ]]
done

CONFLICT_CHECK="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id, telnyx_call_leg_id, telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
[[ "$CONFLICT_CHECK" == $'ccid-a|session-a|leg-a|webhook-a|machine' ]]

if "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', '   ');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL blank call control ID accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-b', NULL, NULL, NULL, 'robot');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL invalid AMD result accepted' >&2
  exit 1
fi

CONSTRAINTS="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_wake_log'::regclass AND contype='c';")"
[[ "$CONSTRAINTS" == "5" ]]
UNIQUE_COUNT="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_wake_log'::regclass AND contype='u';")"
[[ "$UNIQUE_COUNT" == "1" ]]
RLS="$(${PSQL[@]} -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid='public.lm_wake_log'::regclass;")"
[[ "$RLS" == "t" ]]
ROWS="$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_wake_log;")"
[[ "$ROWS" == "3" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF NOT has_function_privilege('service_role', 'public.record_lm_wake_telnyx_receipt(text,text,text,text,text,text,text,text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service_role execute grant absent';
  END IF;
  IF has_function_privilege('anon', 'public.record_lm_wake_telnyx_receipt(text,text,text,text,text,text,text,text)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.record_lm_wake_telnyx_receipt(text,text,text,text,text,text,text,text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser execute grant present';
  END IF;
END $$;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL anon executed Telnyx receipt RPC' >&2
  exit 1
fi

printf '%s\n' 'lm-wake-telnyx-receipt-postgres: PASS latch=1 enrich=1 replay=1 conflicts=7 zero=1 row_preserve=1 unique=1 rls=1 acl=1 rerun=1'
