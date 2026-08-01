#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SUBMISSION_MIGRATION="$ROOT_DIR/migrations/2026-08-02-lm-funder-submission-ledger.sql"
RESULT_MIGRATION="$ROOT_DIR/migrations/2026-08-02-lm-outbound-result-ledger.sql"
DB_NAME="outbound_result_test"
DOCKER_NAME="outbound-result-pg-$$"

cleanup() {
  docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

export PGPASSWORD="outbound-result-test-only"
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

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
SQL
"${PSQL[@]}" -f "$SUBMISSION_MIGRATION" >/dev/null
"${PSQL[@]}" -f "$RESULT_MIGRATION" >/dev/null
"${PSQL[@]}" -f "$RESULT_MIGRATION" >/dev/null

DATABASE_URL="postgresql://postgres:${PGPASSWORD}@127.0.0.1:${PGPORT}/${DB_NAME}" \
  node "$ROOT_DIR/test/postgres/outbound-result-postgres-fixture.js"

[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_outbound_result_ledger")" == "2" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_outbound_current_result")" == "2" ]]
[[ "$("${PSQL[@]}" -Atqc "SELECT relrowsecurity FROM pg_class WHERE oid='public.lm_outbound_result_ledger'::regclass")" == "t" ]]

if "${PSQL[@]}" -c "INSERT INTO public.lm_outbound_result_ledger SELECT * FROM public.lm_outbound_result_ledger WHERE organ='job_hunter';" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL duplicate message/result accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -c "UPDATE public.lm_outbound_result_ledger SET status=status;" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only update succeeded' >&2
  exit 1
fi
if "${PSQL[@]}" -c "DELETE FROM public.lm_outbound_result_ledger;" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only delete succeeded' >&2
  exit 1
fi
if "${PSQL[@]}" -c "TRUNCATE public.lm_outbound_result_ledger;" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only truncate succeeded' >&2
  exit 1
fi
if "${PSQL[@]}" -c "INSERT INTO public.lm_outbound_result_ledger (tenant_id,result_id,organ,workflow,source_kind,source_id,source_fence,entity_id,result_type,status,provider_message_id,provider_thread_id,occurred_at,message_sha256,evidence_sha256,rationale_sha256) VALUES ('tenant-b','outbound-result:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc','fundraising','funder_application','funder_submission','funder-ledger:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',1,'yc-fall-2026','confirmation','confirmed','19fc000000000020','19fc000000000020',now(),repeat('1',64),repeat('2',64),repeat('3',64));" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL fundraising row without content hashes accepted' >&2
  exit 1
fi
if "${PSQL[@]}" -c "SET ROLE service_role; UPDATE public.lm_outbound_result_ledger SET status=status;" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL service_role mutation privilege present' >&2
  exit 1
fi

[[ "$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT count(*) FROM public.lm_outbound_result_ledger")" == "2" ]]
[[ "$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT count(*) FROM public.lm_outbound_current_result")" == "2" ]]
"${PSQL[@]}" >/dev/null <<'SQL'
SET ROLE service_role;
INSERT INTO public.lm_outbound_result_ledger (
  tenant_id,result_id,organ,workflow,source_kind,source_id,source_fence,entity_id,
  result_type,status,provider_message_id,provider_thread_id,occurred_at,
  sender_sha256,subject_sha256,body_sha256,message_sha256,evidence_sha256,rationale_sha256
) VALUES (
  'tenant-a','outbound-result:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
  'job_hunter','job_application','job_submit_intent',
  'job-intent:799cdc72936541f3b03606d998fe2f51',3,
  '3db0cefdf284774c93e0abeee8a72526e345efd8171a2485fd668955a59f53d8',
  'confirmation','confirmed','19fc000000000012','19fc000000000013',
  '2026-08-02T04:00:00Z',NULL,NULL,NULL,repeat('7',64),repeat('8',64),repeat('9',64)
);
SQL
for role in anon authenticated; do
  if "${PSQL[@]}" -c "SET ROLE ${role}; SELECT * FROM public.lm_outbound_result_ledger;" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} table SELECT privilege present" >&2
    exit 1
  fi
  if "${PSQL[@]}" -c "SET ROLE ${role}; SELECT * FROM public.lm_outbound_current_result;" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} view SELECT privilege present" >&2
    exit 1
  fi
  if "${PSQL[@]}" -c "SET ROLE ${role}; INSERT INTO public.lm_outbound_result_ledger (tenant_id) VALUES ('x');" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} table INSERT privilege present" >&2
    exit 1
  fi
done

printf '%s\n' 'outbound-result-postgres: PASS rows=3 store_insert=2 store_replay=2 store_conflict=1 append_only=3 rls=1 roles=3'
