#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-09-lm-travel-block-state.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/lm-travel-block-pg.XXXXXX")"
DB_NAME="lm_travel_block_test"
DB_MODE="local"
DOCKER_NAME="lm-travel-block-pg-$$"

cleanup() {
  if [[ "$DB_MODE" == "docker" ]]; then
    docker rm -f "$DOCKER_NAME" >/dev/null 2>&1 || true
  elif [[ -f "$TEST_TMP/data/postmaster.pid" ]]; then
    pg_ctl -D "$TEST_TMP/data" -m immediate stop >/dev/null 2>&1 || true
  fi
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

if command -v postgres >/dev/null 2>&1; then
  DB_MODE="local"
  mkdir -p "$TEST_TMP/socket"
  initdb -D "$TEST_TMP/data" -A trust --no-locale >/dev/null
  pg_ctl -D "$TEST_TMP/data" -l "$TEST_TMP/postgres.log" -o "-F -h '' -k $TEST_TMP/socket" start >/dev/null
  createdb -h "$TEST_TMP/socket" "$DB_NAME"
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$TEST_TMP/socket" -d "$DB_NAME")
else
  DB_MODE="docker"
  export PGPASSWORD="lm-travel-block-test-only"
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
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE TABLE public.lm_users (
  uid text PRIMARY KEY,
  calendar_composio_user_id text,
  gmail_account_id text
);
INSERT INTO public.lm_users(uid, calendar_composio_user_id, gmail_account_id)
VALUES ('tenant-a', 'owner-a', 'account-a');
CREATE TABLE public.lm_test_provider_posts (
  provider_event_id text PRIMARY KEY,
  connected_account_id text NOT NULL,
  posted_by text NOT NULL
);
SQL

# Applying the production migration itself is part of this test; a regex-only
# assertion cannot detect an invalid function signature or an SQL syntax error.
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT to_regclass('public.lm_travel_log');")" == "public.lm_travel_log" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_travel_log;")" == "0" ]]

# Re-run against an existing legacy table with a row.  The table creation is
# deliberately outside the follow-up migration so this proves both clean
# install and additive preservation of legacy state.
"${PSQL[@]}" >/dev/null <<'SQL'
DROP TABLE public.lm_travel_log CASCADE;
CREATE TABLE public.lm_travel_log (
  uid text NOT NULL,
  event_key text NOT NULL,
  leg text NOT NULL CHECK (leg IN ('go', 'return')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (uid, event_key, leg)
);
INSERT INTO public.lm_travel_log(uid, event_key, leg) VALUES ('tenant-a', 'legacy-event', 'go');
SQL
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_travel_log;")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT status FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='legacy-event' AND leg='go';")" == "legacy_terminal" ]]

# A deploy retry must be idempotent and keep the legacy row.
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_travel_log;")" == "1" ]]

"${PSQL[@]}" >/dev/null <<'SQL'
DO $$
DECLARE
  claim_sig constant text := 'public.claim_lm_travel_block(text,text,text,text,text,text,text,text,text,text,text,integer,timestamp with time zone)';
BEGIN
  IF to_regprocedure(claim_sig) IS NULL THEN
    RAISE EXCEPTION 'new claim signature is missing';
  END IF;
  IF to_regprocedure('public.claim_lm_travel_block(text,text,text,text,text,text,text,text,text,integer,timestamp with time zone)') IS NOT NULL THEN
    RAISE EXCEPTION 'old claim signature remains';
  END IF;
  IF NOT has_function_privilege('service_role', claim_sig, 'EXECUTE') THEN
    RAISE EXCEPTION 'service role claim grant missing';
  END IF;
  IF has_function_privilege('anon', claim_sig, 'EXECUTE') OR has_function_privilege('authenticated', claim_sig, 'EXECUTE') THEN
    RAISE EXCEPTION 'browser claim grant present';
  END IF;
  IF NOT has_function_privilege('service_role', 'public.release_lm_travel_claim(text,text,text,text,text,timestamp with time zone)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service role release grant has the wrong signature';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.lm_travel_log', 'SELECT,INSERT,UPDATE,DELETE') THEN
    RAISE EXCEPTION 'service role travel table grant missing';
  END IF;
END $$;
SQL

PAYLOAD_HASH="$(printf '%064d' 1)"
PROVIDER_EVENT_ID="lmaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
MARKER="lm_travel_v1_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
CLAIM_SQL="SELECT public.claim_lm_travel_block('tenant-a','source-a','go','primary','analysis-a','$PAYLOAD_HASH','$MARKER','$PROVIDER_EVENT_ID','owner-a','account-a','worker',120,'2026-08-10T00:00:00Z'::timestamptz);"

# Two independent sessions race on an absent semantic row.  Both must return
# JSON successfully: one owns the active lease and one is busy, with one row
# and one token.  A worker performs the single provider POST only when it owns
# the durable claim; the provider table is the concrete side-effect ledger.
"${PSQL[@]}" -Atqc "$CLAIM_SQL" >"$TEST_TMP/claim-a.json" &
CLAIM_A_PID=$!
"${PSQL[@]}" -Atqc "$CLAIM_SQL" >"$TEST_TMP/claim-b.json" &
CLAIM_B_PID=$!
wait "$CLAIM_A_PID"
wait "$CLAIM_B_PID"

DECISIONS="$(jq -r '.decision' "$TEST_TMP/claim-a.json" "$TEST_TMP/claim-b.json" | sort | paste -sd, -)"
[[ "$DECISIONS" == "busy,claimed" ]]
TOKENS="$(jq -r '.row.claim_token' "$TEST_TMP/claim-a.json" "$TEST_TMP/claim-b.json" | sort -u | wc -l | tr -d '[:space:]')"
[[ "$TOKENS" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='source-a' AND leg='go';")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT composio_user_id || '|' || connected_account_id FROM public.lm_travel_log WHERE uid='tenant-a' AND event_key='source-a' AND leg='go';")" == "owner-a|account-a" ]]

for claim_file in "$TEST_TMP/claim-a.json" "$TEST_TMP/claim-b.json"; do
  if [[ "$(jq -r '.decision' "$claim_file")" == "claimed" ]]; then
    CLAIM_TOKEN="$(jq -r '.row.claim_token' "$claim_file")"
    CLAIM_ACCOUNT="$(jq -r '.row.connected_account_id' "$claim_file")"
    "${PSQL[@]}" -v ON_ERROR_STOP=1 -c "INSERT INTO public.lm_test_provider_posts(provider_event_id, connected_account_id, posted_by) VALUES ('$PROVIDER_EVENT_ID', '$CLAIM_ACCOUNT', '$CLAIM_TOKEN');" >/dev/null
  fi
done
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_test_provider_posts;")" == "1" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT connected_account_id FROM public.lm_test_provider_posts;")" == "account-a" ]]

# Durable tenant binding is checked before a claim can reach a provider.  A
# caller that supplies another owner/account receives a bounded decision and
# cannot add a provider side effect.
BAD_BINDING="${CLAIM_SQL/owner-a/account-wrong}"
BAD_BINDING="${BAD_BINDING/account-a/account-wrong}"
[[ "$("${PSQL[@]}" -Atqc "$BAD_BINDING" | jq -r '.decision')" == "provider_binding_invalid" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_test_provider_posts;")" == "1" ]]

printf '%s\n' 'mobile-travel-block-postgres: PASS clean_install=1 legacy_preserved=1 rerun=1 concurrent_claims=2 decisions=claimed+busy rows=1 tokens=1 provider_posts=1 binding=fail-closed'
