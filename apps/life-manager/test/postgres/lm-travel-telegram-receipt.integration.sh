#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_MIGRATION="$ROOT_DIR/migrations/2026-06-24-ch1-atomic-dedup.sql"
LEGS_MIGRATION="$ROOT_DIR/migrations/2026-08-28-lm-travel-log-legs.sql"
MIGRATION="$ROOT_DIR/migrations/2026-08-29-lm-travel-telegram-receipt.sql"
if [[ ! -f "$BASE_MIGRATION" || ! -f "$LEGS_MIGRATION" || ! -f "$MIGRATION" ]]; then
  printf '%s\n' 'missing Telegram travel receipt migration' >&2
  exit 1
fi

TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-travel-telegram-receipt-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="lm_travel_telegram_receipt_test"
DB_MODE="local"
DOCKER_NAME="lm-travel-telegram-receipt-pg-$$"

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
  export PGPASSWORD="lm-travel-telegram-receipt-test-only"
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
CREATE TABLE public.lm_ask_log (
  uid text NOT NULL,
  event_id text NOT NULL
);
SQL

"${PSQL[@]}" -f "$BASE_MIGRATION" >/dev/null
"${PSQL[@]}" -f "$LEGS_MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
ALTER TABLE public.lm_travel_log
  ADD CONSTRAINT lm_travel_log_uid_nonempty CHECK (uid <> '');
INSERT INTO public.lm_travel_log(uid, event_key, leg, created_at)
VALUES
  ('tenant-a', 'existing-go', 'go', '2026-08-29T00:00:00Z'),
  ('tenant-a', 'existing-return', 'return', '2026-08-29T00:01:00Z');
SQL

CONSTRAINTS_BEFORE="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_travel_log'::regclass;")"
INDEX_BEFORE="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_travel_log' AND indexname='lm_travel_log_uid_idx';")"
RLS_BEFORE="$(${PSQL[@]} -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid='public.lm_travel_log'::regclass;")"
POLICIES_BEFORE="$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename='lm_travel_log';")"
EXISTING_BEFORE="$(${PSQL[@]} -Atqc "SELECT uid || '|' || event_key || '|' || leg || '|' || created_at::text FROM public.lm_travel_log WHERE event_key LIKE 'existing-%' ORDER BY event_key;")"

"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='lm_travel_log' AND column_name IN ('telegram_message_id','telegram_sent_at');")" "2" "receipt columns"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conname='lm_travel_log_telegram_message_id_check' AND convalidated;")" "1" "validated message check"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_travel_log' AND indexname='lm_travel_log_uid_telegram_message_id_key';")" "1" "receipt partial index"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_proc AS p JOIN pg_namespace AS n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.oid = 'public.record_lm_travel_telegram_receipt(text,text,text,bigint)'::regprocedure;")" "1" "receipt function signature"
assert_eq "$(${PSQL[@]} -Atqc "SELECT prosecdef FROM pg_proc WHERE oid='public.record_lm_travel_telegram_receipt(text,text,text,bigint)'::regprocedure;")" "t" "security definer"
FUNCTION_CONFIG="$(${PSQL[@]} -Atqc "SELECT array_to_string(proconfig, ',') FROM pg_proc WHERE oid='public.record_lm_travel_telegram_receipt(text,text,text,bigint)'::regprocedure;")"
[[ "$FUNCTION_CONFIG" == *"search_path=public, pg_temp"* ]]

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_travel_log(uid, event_key, leg)
VALUES
  ('tenant-a', 'event-a', 'telegram-t5'),
  ('tenant-a', 'event-b', 'telegram-t5'),
  ('tenant-a', 'event-upgrade', 'trial-upgrade'),
  ('tenant-b', 'event-a', 'telegram-t5'),
  ('tenant-a', 'all-legs', 'go'),
  ('tenant-a', 'all-legs', 'return'),
  ('tenant-a', 'all-legs', 'telegram-t5'),
  ('tenant-a', 'all-legs', 'trial-upgrade');
SQL

FIRST="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 101);")"
assert_eq "$FIRST" "1" "first latch"
LATCH="$(${PSQL[@]} -Atqc "SELECT telegram_message_id, telegram_sent_at IS NOT NULL FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='event-a' AND leg='telegram-t5';")"
assert_eq "$LATCH" $'101|t' "latched message and timestamp"
RECEIPT_AT="$(${PSQL[@]} -Atqc "SELECT telegram_sent_at::text FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='event-a' AND leg='telegram-t5';")"

REPLAY="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 101);")"
assert_eq "$REPLAY" "1" "exact replay"
REPLAY_AT="$(${PSQL[@]} -Atqc "SELECT telegram_sent_at::text FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='event-a' AND leg='telegram-t5';")"
assert_eq "$REPLAY_AT" "$RECEIPT_AT" "first timestamp preserved"

CONFLICT="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 202);")"
assert_eq "$CONFLICT" "0" "same-row conflicting ID"
assert_eq "$(${PSQL[@]} -Atqc "SELECT telegram_message_id, telegram_sent_at::text FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='event-a' AND leg='telegram-t5';")" $"101|$RECEIPT_AT" "same-row unchanged"

SAME_UID="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-b', 'telegram-t5', 101);")"
assert_eq "$SAME_UID" "0" "same uid cross-row ID"
SAME_UID_LEG="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-upgrade', 'trial-upgrade', 101);")"
assert_eq "$SAME_UID_LEG" "0" "same uid cross-leg ID"
CROSS_TENANT="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-b', 'event-a', 'telegram-t5', 101);")"
assert_eq "$CROSS_TENANT" "1" "same numeric ID across tenants"
TRIAL="$(${PSQL[@]} -Atqc "SET ROLE service_role; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-upgrade', 'trial-upgrade', 303);")"
assert_eq "$TRIAL" "1" "trial-upgrade leg"

for QUERY in \
  "SELECT public.record_lm_travel_telegram_receipt('', 'event-a', 'telegram-t5', 401)" \
  "SELECT public.record_lm_travel_telegram_receipt(repeat('u', 257), 'event-a', 'telegram-t5', 402)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', '', 'telegram-t5', 403)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', repeat('e', 513), 'telegram-t5', 404)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'go', 405)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'return', 406)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'unknown', 407)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 0)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', -1)" \
  "SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', NULL)"; do
  if "${PSQL[@]}" -Atqc "SET ROLE service_role; $QUERY" >/dev/null 2>&1; then
    printf 'FAIL invalid receipt input accepted: %s\n' "$QUERY" >&2
    exit 1
  fi
done

if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg, telegram_message_id) VALUES ('tenant-a', 'invalid-positive-check', 'telegram-t5', 0);" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL non-positive telegram message ID bypassed CHECK' >&2
  exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'all-legs', 'unknown');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL unknown leg accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'event-a', 'telegram-t5');" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL duplicate travel claim accepted' >&2
  exit 1
fi

assert_eq "$(${PSQL[@]} -Atqc "SELECT uid || '|' || event_key || '|' || leg || '|' || created_at::text FROM public.lm_travel_log WHERE event_key LIKE 'existing-%' ORDER BY event_key;")" "$EXISTING_BEFORE" "preexisting rows and created_at"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conrelid='public.lm_travel_log'::regclass;")" "$((CONSTRAINTS_BEFORE + 1))" "one additive constraint"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_constraint WHERE conname='lm_travel_log_uid_nonempty';")" "1" "unrelated constraint preserved"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='lm_travel_log' AND indexname='lm_travel_log_uid_idx';")" "$INDEX_BEFORE" "uid index preserved"
assert_eq "$(${PSQL[@]} -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid='public.lm_travel_log'::regclass;")" "$RLS_BEFORE" "RLS preserved"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename='lm_travel_log';")" "$POLICIES_BEFORE" "policies preserved"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_travel_log WHERE event_key='all-legs';")" "4" "four-leg rows"
assert_eq "$(${PSQL[@]} -Atqc "SELECT count(*) FROM public.lm_travel_log WHERE telegram_message_id IS NOT NULL;")" "3" "latched rows"

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
BEGIN
  IF NOT has_function_privilege('service_role', 'public.record_lm_travel_telegram_receipt(text,text,text,bigint)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service_role execute grant absent';
  END IF;
  IF has_function_privilege('anon', 'public.record_lm_travel_telegram_receipt(text,text,text,bigint)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.record_lm_travel_telegram_receipt(text,text,text,bigint)', 'EXECUTE') THEN
    RAISE EXCEPTION 'browser execute grant present';
  END IF;
END $$;
SQL

if "${PSQL[@]}" -c "SET ROLE anon; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 101);" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL anon executed Telegram travel receipt RPC' >&2
  exit 1
fi
if "${PSQL[@]}" -c "SET ROLE authenticated; SELECT public.record_lm_travel_telegram_receipt('tenant-a', 'event-a', 'telegram-t5', 101);" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL authenticated executed Telegram travel receipt RPC' >&2
  exit 1
fi

printf '%s\n' 'lm-travel-telegram-receipt-postgres: PASS latch=1 replay=1 conflict=1 same_uid_unique=1 cross_tenant=1 legs=1 rows=1 claim_unique=1 four_leg=1 index=1 rls=1 policies=1 acl=1 rerun=1'
