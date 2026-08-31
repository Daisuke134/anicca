#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-29-lm-wake-telnyx-receipt.sql"
FIX_MIGRATION="$ROOT_DIR/migrations/2026-08-29-z-lm-wake-telnyx-receipt-amd-precedence.sql"
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

assert_eq() {
  local actual="$1"
  local expected="$2"
  local label="${3:-assertion}"
  if [[ "$actual" != "$expected" ]]; then
    printf 'FAIL %s: expected [%s], got [%s]\n' "$label" "$expected" "$actual" >&2
    exit 1
  fi
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

POLICY_BEFORE="$(${PSQL[@]} -Atqc "SELECT policyname || '|' || coalesce(qual::text, '') || '|' || coalesce(with_check::text, '') FROM pg_policies WHERE schemaname='public' AND tablename='lm_wake_log' ORDER BY policyname;")"

"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
if [[ -f "$FIX_MIGRATION" ]]; then
  "${PSQL[@]}" -f "$FIX_MIGRATION" >/dev/null
  "${PSQL[@]}" -f "$FIX_MIGRATION" >/dev/null
fi

POLICY_AFTER="$(${PSQL[@]} -Atqc "SELECT policyname || '|' || coalesce(qual::text, '') || '|' || coalesce(with_check::text, '') FROM pg_policies WHERE schemaname='public' AND tablename='lm_wake_log' ORDER BY policyname;")"
assert_eq "$POLICY_AFTER" "$POLICY_BEFORE" "policies preserved"

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_wake_log(uid, event_key, claim_token, called_at, answered_at)
VALUES
  ('tenant-a', 'event-a', 'claim-a', '2026-08-29T00:00:00Z', '2026-08-29T00:01:00Z'),
  ('tenant-a', 'event-b', 'claim-b', '2026-08-29T00:00:00Z', NULL),
  ('tenant-b', 'event-a', 'claim-other', '2026-08-29T00:00:00Z', NULL),
  ('tenant-a', 'event-hangup-first', 'claim-hangup-first', NULL, NULL),
  ('tenant-a', 'event-amd-first', 'claim-amd-first', NULL, NULL),
  ('tenant-a', 'event-concurrent-hangup-first', 'claim-concurrent-hangup-first', NULL, NULL),
  ('tenant-a', 'event-concurrent-amd-first', 'claim-concurrent-amd-first', NULL, NULL);
SQL

FIRST="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a');")"
assert_eq "$FIRST" "1" "dial latch"
LATCH="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id IS NULL, called_at::text, answered_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$LATCH" $'ccid-a|t|2026-08-29 00:00:00+00|2026-08-29 00:01:00+00' "old wake fields"

SECOND="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'machine');")"
assert_eq "$SECOND" "1" "signed webhook enrichment"
ENRICHED="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id, telnyx_call_leg_id, telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at IS NOT NULL FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$ENRICHED" $'ccid-a|session-a|leg-a|webhook-a|machine|t' "receipt fields"
RECEIVED_AT="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_received_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"

HANGUP_FIRST="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-hangup-first', 'claim-hangup-first', 'ccid-hangup-first', 'session-hangup-first', 'leg-hangup-first', 'webhook-hangup-first');")"
assert_eq "$HANGUP_FIRST" "1" "hangup-first receipt"
HANGUP_FIRST_AT="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_received_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")"
HANGUP_FIRST_REPLAY="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-hangup-first', 'claim-hangup-first', 'ccid-hangup-first', 'session-hangup-first', 'leg-hangup-first', 'webhook-hangup-first');")"
assert_eq "$HANGUP_FIRST_REPLAY" "1" "hangup-first replay"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, telnyx_webhook_received_at::text = '$HANGUP_FIRST_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")" $'webhook-hangup-first|t' "hangup replay preserves receipt"
sleep 0.1
AMD_AFTER_HANGUP="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-hangup-first', 'claim-hangup-first', 'ccid-hangup-first', 'session-hangup-first', 'leg-hangup-first', 'webhook-amd-after-hangup', 'human');")"
assert_eq "$AMD_AFTER_HANGUP" "1" "AMD after hangup"
HANGUP_FIRST_STATE="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")"
assert_eq "$HANGUP_FIRST_STATE" "webhook-amd-after-hangup|human" "AMD wins after hangup"
AMD_AFTER_HANGUP_AT="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_received_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")"
if [[ "$HANGUP_FIRST_AT" == "$AMD_AFTER_HANGUP_AT" ]]; then
  printf '%s\n' 'FAIL AMD receipt timestamp did not replace hangup timestamp' >&2
  exit 1
fi
AMD_REPLAY_AFTER_HANGUP="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-hangup-first', 'claim-hangup-first', 'ccid-hangup-first', 'session-hangup-first', 'leg-hangup-first', 'webhook-amd-after-hangup', 'human');")"
assert_eq "$AMD_REPLAY_AFTER_HANGUP" "1" "AMD replay after hangup"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at::text = '$AMD_AFTER_HANGUP_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")" $'webhook-amd-after-hangup|human|t' "AMD replay preserves receipt"
LATE_HANGUP_AFTER_AMD="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-hangup-first', 'claim-hangup-first', 'ccid-hangup-first', 'session-hangup-first', 'leg-hangup-first', 'webhook-hangup-first');")"
assert_eq "$LATE_HANGUP_AFTER_AMD" "0" "late hangup after AMD"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at::text = '$AMD_AFTER_HANGUP_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-hangup-first';")" $'webhook-amd-after-hangup|human|t' "late hangup preserves AMD"

AMD_FIRST="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-amd-first', 'claim-amd-first', 'ccid-amd-first', 'session-amd-first', 'leg-amd-first', 'webhook-amd-first', 'human');")"
assert_eq "$AMD_FIRST" "1" "AMD-first receipt"
AMD_FIRST_AT="$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_received_at::text FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-amd-first';")"
sleep 0.1
LATE_HANGUP="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-amd-first', 'claim-amd-first', 'ccid-amd-first', 'session-amd-first', 'leg-amd-first', 'webhook-hangup-after-amd');")"
assert_eq "$LATE_HANGUP" "0" "hangup after AMD"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at::text = '$AMD_FIRST_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-amd-first';")" $'webhook-amd-first|human|t' "AMD wins before hangup"
AMD_FIRST_REPLAY="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-amd-first', 'claim-amd-first', 'ccid-amd-first', 'session-amd-first', 'leg-amd-first', 'webhook-amd-first', 'human');")"
assert_eq "$AMD_FIRST_REPLAY" "1" "AMD-first replay"
DIFFERENT_AMD="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-amd-first', 'claim-amd-first', 'ccid-amd-first', 'session-amd-first', 'leg-amd-first', 'webhook-amd-different', 'machine');")"
assert_eq "$DIFFERENT_AMD" "0" "different AMD identity"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result, telnyx_webhook_received_at::text = '$AMD_FIRST_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-amd-first';")" $'webhook-amd-first|human|t' "different AMD leaves row unchanged"

LATER_AMD="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'human');")"
assert_eq "$LATER_AMD" "1" "later AMD human"
REPLAY_CHECK="$(${PSQL[@]} -Atqc "SELECT amd_result, telnyx_webhook_received_at::text = '$RECEIVED_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$REPLAY_CHECK" $'human|t' "last AMD observation and first timestamp"

REPLAY="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'human');")"
assert_eq "$REPLAY" "1" "exact replay"
EXACT_REPLAY_CHECK="$(${PSQL[@]} -Atqc "SELECT amd_result, telnyx_webhook_received_at::text = '$RECEIVED_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$EXACT_REPLAY_CHECK" $'human|t' "exact replay preservation"

LATEST_AMD="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-a', 'not_sure');")"
assert_eq "$LATEST_AMD" "1" "later AMD not_sure"
LATEST_AMD_CHECK="$(${PSQL[@]} -Atqc "SELECT amd_result, telnyx_call_control_id, telnyx_webhook_event_id, telnyx_webhook_received_at::text = '$RECEIVED_AT' FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$LATEST_AMD_CHECK" $'not_sure|ccid-a|webhook-a|t' "latest AMD and first-write IDs"

CALL_ID_COLLISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-a');")"
assert_eq "$CALL_ID_COLLISION" "0" "same call ID across event"
WEBHOOK_ID_COLLISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-b', NULL, NULL, 'webhook-a');")"
assert_eq "$WEBHOOK_ID_COLLISION" "0" "same webhook ID across event"
TENANT_CALL_ID_COLLISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-b', 'event-a', 'claim-other', 'ccid-a');")"
assert_eq "$TENANT_CALL_ID_COLLISION" "0" "same call ID across tenant"
TENANT_WEBHOOK_ID_COLLISION="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-b', 'event-a', 'claim-other', 'ccid-b', NULL, NULL, 'webhook-a');")"
assert_eq "$TENANT_WEBHOOK_ID_COLLISION" "0" "same webhook ID across tenant"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-b' AND telnyx_call_control_id IS NULL AND telnyx_webhook_event_id IS NULL AND amd_result IS NULL;")" "1" "collision row unchanged"

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_wake_log(uid, event_key, claim_token)
VALUES ('tenant-a', 'event-c', 'claim-c'), ('tenant-a', 'event-d', 'claim-d');
SQL

CONCURRENT_ONE="$TEST_TMP/concurrent-one.out"
CONCURRENT_TWO="$TEST_TMP/concurrent-two.out"
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-c', 'claim-c', 'ccid-concurrent'); SELECT pg_sleep(1); COMMIT;" >"$CONCURRENT_ONE"
) &
PID_ONE=$!
sleep 0.1
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-d', 'claim-d', 'ccid-concurrent'); SELECT pg_sleep(1); COMMIT;" >"$CONCURRENT_TWO"
) &
PID_TWO=$!
wait "$PID_ONE"
wait "$PID_TWO"
CONCURRENT_RESULT_ONE="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_ONE")"
CONCURRENT_RESULT_TWO="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_TWO")"
if ! { [[ "$CONCURRENT_RESULT_ONE" == "1" && "$CONCURRENT_RESULT_TWO" == "0" ]] ||
       [[ "$CONCURRENT_RESULT_ONE" == "0" && "$CONCURRENT_RESULT_TWO" == "1" ]]; }; then
  printf 'FAIL concurrent collision results: [%s] and [%s]\n' "$CONCURRENT_RESULT_ONE" "$CONCURRENT_RESULT_TWO" >&2
  exit 1
fi
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_wake_log WHERE telnyx_call_control_id='ccid-concurrent';")" "1" "one concurrent winner"

CONCURRENT_HANGUP_FIRST_H="$TEST_TMP/concurrent-hangup-first-h.out"
CONCURRENT_HANGUP_FIRST_A="$TEST_TMP/concurrent-hangup-first-a.out"
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-concurrent-hangup-first', 'claim-concurrent-hangup-first', 'ccid-concurrent-hangup-first', 'session-concurrent-hangup-first', 'leg-concurrent-hangup-first', 'webhook-concurrent-hangup-first'); SELECT pg_sleep(1); COMMIT;" >"$CONCURRENT_HANGUP_FIRST_H"
) &
PID_HANGUP_FIRST_H=$!
sleep 0.1
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-concurrent-hangup-first', 'claim-concurrent-hangup-first', 'ccid-concurrent-hangup-first', 'session-concurrent-hangup-first', 'leg-concurrent-hangup-first', 'webhook-concurrent-hangup-first-amd', 'human'); COMMIT;" >"$CONCURRENT_HANGUP_FIRST_A"
) &
PID_HANGUP_FIRST_A=$!
wait "$PID_HANGUP_FIRST_H"
wait "$PID_HANGUP_FIRST_A"
CONCURRENT_HANGUP_FIRST_H_RESULT="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_HANGUP_FIRST_H")"
CONCURRENT_HANGUP_FIRST_A_RESULT="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_HANGUP_FIRST_A")"
assert_eq "$CONCURRENT_HANGUP_FIRST_H_RESULT|$CONCURRENT_HANGUP_FIRST_A_RESULT" "1|1" "hangup-first concurrent receipts"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-concurrent-hangup-first';")" "webhook-concurrent-hangup-first-amd|human" "hangup-first concurrent AMD precedence"

CONCURRENT_AMD_FIRST_A="$TEST_TMP/concurrent-amd-first-a.out"
CONCURRENT_AMD_FIRST_H="$TEST_TMP/concurrent-amd-first-h.out"
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-concurrent-amd-first', 'claim-concurrent-amd-first', 'ccid-concurrent-amd-first', 'session-concurrent-amd-first', 'leg-concurrent-amd-first', 'webhook-concurrent-amd-first-amd', 'machine'); SELECT pg_sleep(1); COMMIT;" >"$CONCURRENT_AMD_FIRST_A"
) &
PID_AMD_FIRST_A=$!
sleep 0.1
(
  "${PSQL[@]}" -Atqc "BEGIN; SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-concurrent-amd-first', 'claim-concurrent-amd-first', 'ccid-concurrent-amd-first', 'session-concurrent-amd-first', 'leg-concurrent-amd-first', 'webhook-concurrent-amd-first-hangup'); COMMIT;" >"$CONCURRENT_AMD_FIRST_H"
) &
PID_AMD_FIRST_H=$!
wait "$PID_AMD_FIRST_A"
wait "$PID_AMD_FIRST_H"
CONCURRENT_AMD_FIRST_A_RESULT="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_AMD_FIRST_A")"
CONCURRENT_AMD_FIRST_H_RESULT="$(awk '/^(0|1)$/{print; exit}' "$CONCURRENT_AMD_FIRST_H")"
assert_eq "$CONCURRENT_AMD_FIRST_A_RESULT|$CONCURRENT_AMD_FIRST_H_RESULT" "1|0" "AMD-first concurrent receipts"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-concurrent-amd-first';")" "webhook-concurrent-amd-first-amd|machine" "AMD-first concurrent precedence"

ORIGINAL_AFTER_CONCURRENT="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$ORIGINAL_AFTER_CONCURRENT" $'ccid-a|webhook-a|not_sure' "original row after concurrent collision"

for QUERY in \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-other', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-b', 'event-a', 'claim-other', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-a')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-other')" \
  "SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-a', 'claim-a', 'ccid-a', 'session-a', 'leg-a', 'webhook-other')"; do
  MATCHED="$(${PSQL[@]} -Atqc "SET ROLE service_role; $QUERY;")"
  assert_eq "$MATCHED" "0" "same-row conflicting identity"
done

CONFLICT_CHECK="$(${PSQL[@]} -Atqc "SELECT telnyx_call_control_id, telnyx_call_session_id, telnyx_call_leg_id, telnyx_webhook_event_id, amd_result FROM public.lm_wake_log WHERE uid='tenant-a' AND event_key='event-a';")"
assert_eq "$CONFLICT_CHECK" $'ccid-a|session-a|leg-a|webhook-a|not_sure' "original row after conflicts"

if "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', '   ');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL blank call control ID accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.record_lm_wake_telnyx_receipt('tenant-a', 'event-b', 'claim-b', 'ccid-b', NULL, NULL, NULL, 'robot');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL invalid AMD result accepted' >&2
  exit 1
fi

CONSTRAINTS="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_wake_log'::regclass AND contype='c';")"
assert_eq "$CONSTRAINTS" "5" "constraints preserved"
UNIQUE_COUNT="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_wake_log'::regclass AND contype='u';")"
assert_eq "$UNIQUE_COUNT" "1" "wake unique key preserved"
PROVIDER_INDEX_COUNT="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_wake_log' AND indexname IN ('lm_wake_log_telnyx_call_control_id_key', 'lm_wake_log_telnyx_webhook_event_id_key');")"
assert_eq "$PROVIDER_INDEX_COUNT" "2" "provider unique indexes"
RLS="$(${PSQL[@]} -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid='public.lm_wake_log'::regclass;")"
assert_eq "$RLS" "t" "RLS preserved"
ROWS="$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_wake_log;")"
assert_eq "$ROWS" "9" "rows preserved"

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

printf '%s\n' 'lm-wake-telnyx-receipt-postgres: PASS latch=1 enrich=1 amd_precedence=1 replay=1 conflicts=7 cross_row=1 concurrent_unique=1 concurrent_precedence=2 zero=1 row_preserve=1 unique=1 provider_indexes=2 policies=1 rls=1 acl=1 rerun=1'
