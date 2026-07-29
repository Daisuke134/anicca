#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/20260729_runtime_jobs.sql"
AGING_MIGRATION="$ROOT_DIR/migrations/20260730_runtime_reconcile_unknown_aging.sql"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/runtime-job-pg.XXXXXX")"
DB_NAME="runtime_job_test"
DOCKER_NAME="runtime-job-pg-$$"

cleanup() {
  docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT INT TERM

export PGPASSWORD="runtime-job-test-only"
docker run --rm -d \
  --name "$DOCKER_NAME" \
  -e POSTGRES_PASSWORD="$PGPASSWORD" \
  -e POSTGRES_DB="$DB_NAME" \
  -p 127.0.0.1::5432 \
  postgres:18-alpine >/dev/null

MAPPED="$(docker port "$DOCKER_NAME" 5432/tcp)"
PGPORT="${MAPPED##*:}"
for _ in {1..100}; do
  if pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done
pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null

PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME")
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$AGING_MIGRATION" >/dev/null

scalar() {
  "${PSQL[@]}" -Atqc "$1"
}

insert_job() {
  local job_id="$1"
  local capability="$2"
  local effect_class="$3"
  local effect_key_sql="$4"
  local max_attempts="${5:-3}"
  "${PSQL[@]}" -v ON_ERROR_STOP=1 -v \
    job_id="$job_id" -v capability="$capability" -v \
    effect_class="$effect_class" -v effect_key_sql="$effect_key_sql" -v \
    max_attempts="$max_attempts" >/dev/null <<'SQL'
INSERT INTO public.lm_runtime_jobs (
  job_id, tenant_id, loop_id, capability, effect_class, effect_key, input_refs, max_attempts
) VALUES (
  :'job_id',
  'tenant-a',
  'integration.runtime',
  :'capability',
  :'effect_class',
  CASE WHEN :'effect_key_sql' = 'NULL' THEN NULL ELSE :'effect_key_sql' END,
  jsonb_build_object('fixture_ref', 'fixture:' || :'job_id'),
  :'max_attempts'
)
ON CONFLICT (job_id) DO NOTHING;
SQL
}

restart_pass() {
  insert_job \
    "restart-stable" \
    "integration.restart-stable" \
    "publish" \
    "tiktok:tenant-a:restart-stable"
  [[ "$(scalar "SELECT count(*) FROM public.lm_runtime_jobs WHERE job_id='restart-stable' AND effect_key='tiktok:tenant-a:restart-stable';")" == "1" ]]
}

restart_pass
restart_pass
printf '%s\n' 'runtime job postgres enqueue pass 1 + pass 2: ok'

if "${PSQL[@]}" -c "
  INSERT INTO public.lm_runtime_jobs (
    job_id, tenant_id, loop_id, capability, effect_class, effect_key, input_refs, max_attempts
  ) VALUES (
    'effect-key-collision', 'tenant-a', 'integration.runtime',
    'integration.effect-key-collision', 'publish',
    'tiktok:tenant-a:restart-stable', '{\"fixture_ref\":\"fixture:collision\"}'::jsonb, 3
  );" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL duplicate external effect key accepted' >&2
  exit 1
fi

[[ "$(scalar "SELECT count(*) FROM public.claim_lm_runtime_jobs('wrong-capability-worker', ARRAY['integration.unrelated'], 'tenant-a', 1, 60);")" == "0" ]]
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('stable-worker', ARRAY['integration.restart-stable'], 'tenant-a', 1, 60);")" == "1" ]]
[[ "$(scalar "SELECT count(*) FROM public.heartbeat_lm_runtime_job('tenant-b', 'restart-stable', 1, 'stable-worker', 60);")" == "0" ]]
[[ "$(scalar "SELECT count(*) FROM public.complete_lm_runtime_job('tenant-a', 'restart-stable', 1, 'stable-worker', '{\"provider_id\":\"post-stable\"}'::jsonb);")" == "1" ]]
[[ "$(scalar "SELECT count(*) FROM public.complete_lm_runtime_job('tenant-a', 'restart-stable', 1, 'stable-worker', '{\"provider_id\":\"post-stable\"}'::jsonb);")" == "1" ]]
if "${PSQL[@]}" -c "
  SELECT public.complete_lm_runtime_job(
    'tenant-a', 'restart-stable', 1, 'stable-worker', '{\"provider_id\":\"changed\"}'::jsonb
  );" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL conflicting completion receipt accepted' >&2
  exit 1
fi

insert_job "one-claimant" "integration.one-claimant" "none" "NULL"
"${PSQL[@]}" -Atqc "
  SELECT count(*) FROM public.claim_lm_runtime_jobs(
    'claimant-a', ARRAY['integration.one-claimant'], 'tenant-a', 1, 60
  );" >"$TEST_TMP/claim-a.out" &
CLAIM_A_PID=$!
"${PSQL[@]}" -Atqc "
  SELECT count(*) FROM public.claim_lm_runtime_jobs(
    'claimant-b', ARRAY['integration.one-claimant'], 'tenant-a', 1, 60
  );" >"$TEST_TMP/claim-b.out" &
CLAIM_B_PID=$!
wait "$CLAIM_A_PID"
wait "$CLAIM_B_PID"
CLAIM_TOTAL="$(( $(<"$TEST_TMP/claim-a.out") + $(<"$TEST_TMP/claim-b.out") ))"
[[ "$CLAIM_TOTAL" == "1" ]]

insert_job "lease-expiry" "integration.lease-expiry" "none" "NULL"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('lease-worker-a', ARRAY['integration.lease-expiry'], 'tenant-a', 1, 60);")" == "1" ]]
"${PSQL[@]}" -c "
  UPDATE public.lm_runtime_jobs
  SET lease_expires_at = clock_timestamp() - interval '1 second'
  WHERE job_id = 'lease-expiry';" >/dev/null
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('lease-worker-b', ARRAY['integration.lease-expiry'], 'tenant-a', 1, 60);")" == "2" ]]
[[ "$(scalar "SELECT lease_owner FROM public.lm_runtime_jobs WHERE job_id='lease-expiry';")" == "lease-worker-b" ]]

insert_job "bounded-retry" "integration.bounded-retry" "none" "NULL" "2"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('retry-worker', ARRAY['integration.bounded-retry'], 'tenant-a', 1, 60);")" == "1" ]]
[[ "$(scalar "SELECT status FROM public.fail_lm_runtime_job('tenant-a', 'bounded-retry', 1, 'retry-worker', 'FIXTURE_FAILURE', false);")" == "queued" ]]
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('retry-worker', ARRAY['integration.bounded-retry'], 'tenant-a', 1, 60);")" == "2" ]]
[[ "$(scalar "SELECT status FROM public.fail_lm_runtime_job('tenant-a', 'bounded-retry', 2, 'retry-worker', 'FIXTURE_FAILURE', false);")" == "dead_letter" ]]
[[ "$(scalar "SELECT count(*) FROM public.lm_runtime_job_receipts WHERE job_id='bounded-retry';")" == "2" ]]

insert_job \
  "unknown-effect" \
  "integration.unknown-effect" \
  "publish" \
  "instagram:tenant-a:unknown-effect"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('effect-worker', ARRAY['integration.unknown-effect'], 'tenant-a', 1, 60);")" == "1" ]]
[[ "$(scalar "SELECT status FROM public.fail_lm_runtime_job('tenant-a', 'unknown-effect', 1, 'effect-worker', 'PROVIDER_TIMEOUT', true);")" == "reconciling" ]]
[[ "$(scalar "SELECT count(*) FROM public.lm_runtime_job_receipts WHERE job_id='unknown-effect';")" == "0" ]]
[[ "$(scalar "SELECT status FROM public.resolve_lm_runtime_effect('tenant-a', 'unknown-effect', 1, 'absent', '{\"lookup\":\"provider_not_found\"}'::jsonb);")" == "queued" ]]
[[ "$(scalar "SELECT status FROM public.resolve_lm_runtime_effect('tenant-a', 'unknown-effect', 1, 'absent', '{\"lookup\":\"provider_not_found\"}'::jsonb);")" == "queued" ]]
[[ "$(scalar "SELECT count(*) FROM public.lm_runtime_job_receipts WHERE job_id='unknown-effect' AND attempt=1;")" == "1" ]]
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('effect-worker', ARRAY['integration.unknown-effect'], 'tenant-a', 1, 60);")" == "2" ]]
[[ "$(scalar "SELECT count(*) FROM public.complete_lm_runtime_job('tenant-a', 'unknown-effect', 2, 'effect-worker', '{\"provider_id\":\"post-after-proof\"}'::jsonb);")" == "1" ]]

insert_job \
  "expired-effect" \
  "integration.expired-effect" \
  "message" \
  "telegram:tenant-a:expired-effect"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('message-worker-a', ARRAY['integration.expired-effect'], 'tenant-a', 1, 60);")" == "1" ]]
"${PSQL[@]}" -c "
  UPDATE public.lm_runtime_jobs
  SET lease_expires_at = clock_timestamp() - interval '1 second'
  WHERE job_id = 'expired-effect';" >/dev/null
[[ "$(scalar "SELECT count(*) FROM public.claim_lm_runtime_jobs('message-worker-b', ARRAY['integration.expired-effect'], 'tenant-a', 1, 60);")" == "0" ]]
[[ "$(scalar "SELECT status FROM public.lm_runtime_jobs WHERE job_id='expired-effect';")" == "reconciling" ]]

# Unknown-aging: 4 unknown reconcile results keep the effect quarantined; the 5th
# dead-letters it with RECONCILE_UNKNOWN_EXHAUSTED, and resolution resets the counter.
insert_job \
  "unknown-aging" \
  "integration.unknown-aging" \
  "publish" \
  "instagram:tenant-a:unknown-aging"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('aging-worker', ARRAY['integration.unknown-aging'], 'tenant-a', 1, 60);")" == "1" ]]
[[ "$(scalar "SELECT status FROM public.fail_lm_runtime_job('tenant-a', 'unknown-aging', 1, 'aging-worker', 'PROVIDER_TIMEOUT', true);")" == "reconciling" ]]
for _ in 1 2 3 4; do
  [[ "$(scalar "SELECT status FROM public.age_lm_runtime_reconciliation('tenant-a', 'unknown-aging', 1, 5);")" == "reconciling" ]]
done
[[ "$(scalar "SELECT reconcile_attempts FROM public.lm_runtime_jobs WHERE job_id='unknown-aging';")" == "4" ]]
[[ "$(scalar "SELECT status FROM public.age_lm_runtime_reconciliation('tenant-a', 'unknown-aging', 1, 5);")" == "dead_letter" ]]
[[ "$(scalar "SELECT last_error_code FROM public.lm_runtime_jobs WHERE job_id='unknown-aging';")" == "RECONCILE_UNKNOWN_EXHAUSTED" ]]
[[ "$(scalar "SELECT count(*) FROM public.lm_runtime_job_receipts WHERE job_id='unknown-aging' AND outcome='failed';")" == "1" ]]
[[ "$(scalar "SELECT count(*) FROM public.age_lm_runtime_reconciliation('tenant-a', 'unknown-aging', 1, 5);")" == "0" ]]

insert_job \
  "unknown-aging-reset" \
  "integration.unknown-aging-reset" \
  "publish" \
  "instagram:tenant-a:unknown-aging-reset"
[[ "$(scalar "SELECT attempt FROM public.claim_lm_runtime_jobs('aging-worker', ARRAY['integration.unknown-aging-reset'], 'tenant-a', 1, 60);")" == "1" ]]
[[ "$(scalar "SELECT status FROM public.fail_lm_runtime_job('tenant-a', 'unknown-aging-reset', 1, 'aging-worker', 'PROVIDER_TIMEOUT', true);")" == "reconciling" ]]
[[ "$(scalar "SELECT status FROM public.age_lm_runtime_reconciliation('tenant-a', 'unknown-aging-reset', 1, 5);")" == "reconciling" ]]
[[ "$(scalar "SELECT status FROM public.resolve_lm_runtime_effect('tenant-a', 'unknown-aging-reset', 1, 'absent', '{\"lookup\":\"provider_not_found\"}'::jsonb);")" == "queued" ]]
[[ "$(scalar "SELECT reconcile_attempts FROM public.lm_runtime_jobs WHERE job_id='unknown-aging-reset';")" == "0" ]]
printf '%s\n' 'runtime job postgres unknown-aging dead-letter + reset: ok'

if "${PSQL[@]}" -c "
  UPDATE public.lm_runtime_job_receipts
  SET receipt = '{}'::jsonb
  WHERE job_id = 'restart-stable';" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL immutable receipt update succeeded' >&2
  exit 1
fi
if "${PSQL[@]}" -c "
  DELETE FROM public.lm_runtime_job_receipts
  WHERE job_id = 'restart-stable';" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL immutable receipt delete succeeded' >&2
  exit 1
fi

restart_pass
[[ "$(scalar "SELECT count(*) FROM public.lm_runtime_job_receipts WHERE job_id='restart-stable' AND attempt=1;")" == "1" ]]
printf '%s\n' 'runtime job postgres tenant/lease/retry/reconciliation/receipt: ok'
