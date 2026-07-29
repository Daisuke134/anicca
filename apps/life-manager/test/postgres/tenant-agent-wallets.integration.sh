#!/usr/bin/env bash
# AE-ZERO-START-1 §4.1 / §5.3 — prove the tenant agent wallet constraints in a real PostgreSQL.
#
# lib/agent-wallet-migration.test.js pins the migration's TEXT and behaviour-tests its regexes, but only
# an engine can prove a CHECK actually refuses an INSERT. §5.3 says plaintext keys in the database are 0
# "by schema, not by convention", and that claim is only true if the engine says so — so this script
# writes real rows and requires the refusals.
#
# Prefers a local initdb cluster (same choice as panel-score-postgres.integration.sh) and falls back to
# docker postgres:18-alpine.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_MIGRATION="$ROOT_DIR/migrations/2026-07-27-lm-financial-reports.sql"
MIGRATION="$ROOT_DIR/migrations/2026-07-30-lm-tenant-agent-wallets.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/tenant-agent-wallets-pg.XXXXXX")"
PGDATA_DIR="$TEST_TMP/data"
PGSOCKET_DIR="$TEST_TMP/socket"
PGLOG="$TEST_TMP/postgres.log"
DB_NAME="tenant_agent_wallets_test"
DB_MODE="local"
DOCKER_NAME="tenant-agent-wallets-pg-$$"

cleanup() {
  if [[ "$DB_MODE" == "docker" ]]; then
    docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true
  elif [[ -f "$PGDATA_DIR/postmaster.pid" ]]; then
    pg_ctl -D "$PGDATA_DIR" -m immediate stop >/dev/null 2>&1 || true
  fi
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

# `postgres` is checked explicitly, not just initdb/pg_ctl: a libpq-only install (Homebrew `libpq`) ships
# the client wrappers without a server, and initdb then dies after the cluster directory already exists.
if command -v initdb >/dev/null 2>&1 \
  && command -v pg_ctl >/dev/null 2>&1 \
  && command -v postgres >/dev/null 2>&1 \
  && command -v createdb >/dev/null 2>&1; then
  mkdir -p "$PGSOCKET_DIR"
  initdb -D "$PGDATA_DIR" -A trust --no-locale >/dev/null
  pg_ctl -D "$PGDATA_DIR" -l "$PGLOG" -o "-F -h '' -k $PGSOCKET_DIR" start >/dev/null
  createdb -h "$PGSOCKET_DIR" "$DB_NAME"
  PSQL=(psql -X -v ON_ERROR_STOP=1 -h "$PGSOCKET_DIR" -d "$DB_NAME")
else
  DB_MODE="docker"
  export PGPASSWORD="tenant-agent-wallets-test-only"
  docker run --rm -d --name "$DOCKER_NAME" -e POSTGRES_PASSWORD="$PGPASSWORD" \
    -e POSTGRES_DB="$DB_NAME" -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
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
CREATE TABLE public.lm_api_cost(uid text NOT NULL, ts timestamptz NOT NULL, est_usd numeric NOT NULL);
INSERT INTO public.lm_users(uid) VALUES ('tenant-a'), ('tenant-b');
SQL

# The EVM column and its CHECK come from REPORT-1; this slice is additive on top of it. Applying both in
# order also proves the new migration does not disturb the existing constraint.
"${PSQL[@]}" -f "$REPORT_MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
# Idempotence: the migration must be safe to re-run, since runtime migrate replays the directory.
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

refuses() {
  local label="$1" statement="$2"
  if "${PSQL[@]}" -q -c "$statement" >/dev/null 2>&1; then
    printf 'FAIL %s was ACCEPTED by the database\n' "$label" >&2
    exit 1
  fi
}

accepts() {
  local label="$1" statement="$2"
  if ! "${PSQL[@]}" -q -c "$statement" >/dev/null 2>&1; then
    printf 'FAIL %s was REFUSED by the database\n' "$label" >&2
    exit 1
  fi
}

HEX64="abababababababababababababababababababababababababababababababab"
B58_SECRET="2222222222222222222222222222222222222222222222222222222222222222222222222222222222222222"
SOLANA_A="FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z"
SOLANA_B="586Z7H2vpX9qNhN2T4e9Utugie3ogjbxzGaMtM3E6HR5"
EVM_A="0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

# --- the columns exist, nullable, and a real provisioning row is accepted -------------------------
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='lm_users' AND column_name IN ('agent_wallet_solana_address','agent_wallet_key_ref','agent_wallet_solana_key_ref','agent_wallet_created_at');")" == "4" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='lm_users' AND column_name LIKE 'agent_wallet%' AND is_nullable='NO';")" == "0" ]]

accepts 'a full tenant-a provisioning row' "UPDATE public.lm_users SET agent_wallet_address='$EVM_A', agent_wallet_solana_address='$SOLANA_A', agent_wallet_key_ref='secret://lm-agent-wallet/tenant-a/base', agent_wallet_solana_key_ref='secret://lm-agent-wallet/tenant-a/solana', agent_wallet_created_at=now() WHERE uid='tenant-a';"

# --- §5.3: nothing key-shaped can be stored in a key-ref column ----------------------------------
refuses 'a raw 0x EVM private key as a key ref' "UPDATE public.lm_users SET agent_wallet_key_ref='0x$HEX64' WHERE uid='tenant-b';"
refuses 'a bare 64-hex private key as a key ref' "UPDATE public.lm_users SET agent_wallet_key_ref='$HEX64' WHERE uid='tenant-b';"
refuses 'a base58 Solana secret key as a key ref' "UPDATE public.lm_users SET agent_wallet_solana_key_ref='$B58_SECRET' WHERE uid='tenant-b';"
refuses 'a private key smuggled inside a secret:// reference' "UPDATE public.lm_users SET agent_wallet_key_ref='secret://lm-agent-wallet/tenant-b/$HEX64' WHERE uid='tenant-b';"
refuses 'a Solana secret smuggled inside a secret:// reference' "UPDATE public.lm_users SET agent_wallet_solana_key_ref='secret://lm-agent-wallet/$B58_SECRET' WHERE uid='tenant-b';"
refuses 'a filesystem path instead of a reference' "UPDATE public.lm_users SET agent_wallet_key_ref='/Users/anicca/.anicca/wallets/tenant-b/base.json' WHERE uid='tenant-b';"
refuses 'a bare path with no scheme' "UPDATE public.lm_users SET agent_wallet_key_ref='lm-agent-wallet/tenant-b/base' WHERE uid='tenant-b';"
refuses 'a scheme with no path' "UPDATE public.lm_users SET agent_wallet_key_ref='secret://' WHERE uid='tenant-b';"

# --- the Solana address column only accepts base58 in the ledger's shape --------------------------
refuses 'an EVM address in the Solana column' "UPDATE public.lm_users SET agent_wallet_solana_address='$EVM_A' WHERE uid='tenant-b';"
refuses 'a base58-illegal address (contains 0, O, I, l)' "UPDATE public.lm_users SET agent_wallet_solana_address='0OIl0OIl0OIl0OIl0OIl0OIl0OIl0OIl' WHERE uid='tenant-b';"
refuses 'an over-long address' "UPDATE public.lm_users SET agent_wallet_solana_address='$(printf '1%.0s' {1..45})' WHERE uid='tenant-b';"

# --- the EVM CHECK REPORT-1 installed still works ------------------------------------------------
refuses 'a Solana address in the EVM column' "UPDATE public.lm_users SET agent_wallet_address='$SOLANA_A' WHERE uid='tenant-b';"

# --- tenant isolation is enforced by the engine, not by the writer --------------------------------
refuses "tenant-b claiming tenant-a's Solana address" "UPDATE public.lm_users SET agent_wallet_solana_address='$SOLANA_A' WHERE uid='tenant-b';"
refuses "tenant-b claiming tenant-a's base key ref" "UPDATE public.lm_users SET agent_wallet_key_ref='secret://lm-agent-wallet/tenant-a/base' WHERE uid='tenant-b';"
refuses "tenant-b claiming tenant-a's Solana key ref" "UPDATE public.lm_users SET agent_wallet_solana_key_ref='secret://lm-agent-wallet/tenant-a/solana' WHERE uid='tenant-b';"
accepts "tenant-b's own distinct wallets" "UPDATE public.lm_users SET agent_wallet_solana_address='$SOLANA_B', agent_wallet_key_ref='secret://lm-agent-wallet/tenant-b/base', agent_wallet_solana_key_ref='secret://lm-agent-wallet/tenant-b/solana', agent_wallet_created_at=now() WHERE uid='tenant-b';"

# --- and after all of that, no key material is anywhere in the table -----------------------------
LEAKS="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE agent_wallet_key_ref ~ '[0-9a-fA-F]{64}' OR agent_wallet_solana_key_ref ~ '[0-9a-fA-F]{64}' OR agent_wallet_key_ref ~ '[1-9A-HJ-NP-Za-km-z]{80,}' OR agent_wallet_solana_key_ref ~ '[1-9A-HJ-NP-Za-km-z]{80,}';")"
[[ "$LEAKS" == "0" ]]

PROVISIONED="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_users WHERE agent_wallet_solana_address IS NOT NULL AND agent_wallet_key_ref IS NOT NULL AND agent_wallet_solana_key_ref IS NOT NULL AND agent_wallet_created_at IS NOT NULL;")"
[[ "$PROVISIONED" == "2" ]]

printf '%s\n' "tenant-agent-wallets: PASS mode=$DB_MODE provisioned_tenants=$PROVISIONED refusals=15 key_material_rows=$LEAKS"
