#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-02-lm-funder-weekly-reflection-ledger.sql"
DB_NAME="funder_weekly_reflection_test"
DOCKER_NAME="funder-weekly-reflection-pg-$$"
cleanup() { docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

export PGPASSWORD="funder-weekly-reflection-test-only"
docker run --rm -d --name "$DOCKER_NAME" \
  -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB_NAME" \
  -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
MAPPED="$(docker port "$DOCKER_NAME" 5432/tcp)"
PGPORT="${MAPPED##*:}"
for _ in {1..100}; do
  pg_isready -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME" >/dev/null 2>&1 && break
  sleep 0.1
done
PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PGPORT" -U postgres -d "$DB_NAME")

"${PSQL[@]}" >/dev/null <<'SQL'
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE TABLE public.lm_funder_outreach_ledger (
  tenant_id text NOT NULL, outreach_id text NOT NULL,
  batch_id text NOT NULL, tokyo_date date NOT NULL, candidate_id text NOT NULL,
  funder_name text NOT NULL, recipient_sha256 text NOT NULL, source_url text NOT NULL,
  source_observed_at timestamptz NOT NULL, source_digest text NOT NULL,
  fit_summary_sha256 text NOT NULL, subject_sha256 text NOT NULL, body_sha256 text NOT NULL,
  sent_at timestamptz NOT NULL, provider_message_id text NOT NULL,
  provider_thread_id text NOT NULL, investor_kind text,
  thesis_evidence_sha256 text, company_evidence_sha256 text,
  personalization_sha256 text, daily_slot integer,
  PRIMARY KEY (tenant_id,outreach_id)
);
SQL
"${PSQL[@]}" -f "$MIGRATION" >/dev/null
"${PSQL[@]}" -f "$MIGRATION" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_funder_weekly_reflection_ledger (
 tenant_id,reflection_id,week_key,week_start,week_end,reflected_at,snapshot_digest,
 decision,reason,summary_sha256,rationale_sha256,outcome_result_ids,
 ranked_candidate_ids,pitch_directives
) VALUES (
 'tenant-a','funder-weekly-reflection:'||repeat('a',64),'2026-07-27',
 '2026-07-26T15:00:00Z','2026-08-02T11:15:00Z','2026-08-02T12:00:00Z',repeat('b',64),
 'change','agent_revision',repeat('c',64),repeat('d',64),'["result:meeting"]',
 '["alpha"]',jsonb_build_array(jsonb_build_object(
   'candidate_id','alpha','directive','Use the verified workflow sentence.',
   'directive_sha256',repeat('e',64),'outcome_result_ids',jsonb_build_array('result:meeting')
 ))
);
INSERT INTO public.lm_funder_weekly_reflection_ledger
SELECT 'tenant-b',reflection_id,week_key,week_start,week_end,reflected_at,snapshot_digest,
 decision,reason,summary_sha256,rationale_sha256,outcome_result_ids,ranked_candidate_ids,
 pitch_directives,clock_timestamp()
FROM public.lm_funder_weekly_reflection_ledger WHERE tenant_id='tenant-a';

BEGIN;
INSERT INTO public.lm_funder_outreach_ledger VALUES (
 'tenant-a','funder-outreach:'||repeat('1',64),'funder-outreach-batch:'||repeat('1',64),
 '2026-08-03','alpha','Alpha',repeat('1',64),'https://example.com','2026-08-03T00:00:00Z',
 repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),'2026-08-03T01:00:00Z',
 '19fa000000000001','19fa000000000001','vc',repeat('6',64),repeat('7',64),repeat('8',64),1
);
INSERT INTO public.lm_funder_outreach_reflection_application (
 tenant_id,outreach_id,reflection_id,week_key,ranking_position,pitch_directive_sha256,outcome_result_ids
) VALUES (
 'tenant-a','funder-outreach:'||repeat('1',64),'funder-weekly-reflection:'||repeat('a',64),
 '2026-07-27',1,repeat('e',64),'["result:meeting"]'
);
COMMIT;
SQL

if "${PSQL[@]}" >/dev/null 2>&1 <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger VALUES (
 'tenant-b','funder-outreach:'||repeat('2',64),'funder-outreach-batch:'||repeat('2',64),
 '2026-08-03','not-ranked','Not Ranked',repeat('9',64),'https://example.com','2026-08-03T00:00:00Z',
 repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),'2026-08-03T01:01:00Z',
 '19fa000000000002','19fa000000000002','vc',repeat('6',64),repeat('7',64),repeat('8',64),2
);
SQL
then
  printf '%s\n' 'FAIL outreach without current reflection application inserted' >&2
  exit 1
fi

if "${PSQL[@]}" >/dev/null 2>&1 <<'SQL'
BEGIN;
INSERT INTO public.lm_funder_outreach_ledger VALUES (
 'tenant-a','funder-outreach:'||repeat('3',64),'funder-outreach-batch:'||repeat('3',64),
 '2026-08-03','alpha','Alpha',repeat('a',64),'https://example.com','2026-08-03T00:00:00Z',
 repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),'2026-08-03T01:02:00Z',
 '19fa000000000003','19fa000000000003','vc',repeat('6',64),repeat('7',64),repeat('8',64),3
);
INSERT INTO public.lm_funder_outreach_reflection_application VALUES (
 'tenant-a','funder-outreach:'||repeat('3',64),'funder-weekly-reflection:'||repeat('a',64),
 '2026-07-27',1,repeat('f',64),'["result:meeting"]',clock_timestamp()
);
COMMIT;
SQL
then
  printf '%s\n' 'FAIL tampered directive proof inserted' >&2
  exit 1
fi

if "${PSQL[@]}" -c "UPDATE public.lm_funder_weekly_reflection_ledger SET decision='hold'" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL append-only reflection mutated' >&2
  exit 1
fi
for role in anon authenticated; do
  if "${PSQL[@]}" -c "SET ROLE ${role}; SELECT * FROM public.lm_funder_weekly_reflection_ledger" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} read reflection ledger" >&2
    exit 1
  fi
done
COUNT="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_funder_outreach_reflection_application")"
[[ "$COUNT" == "1" ]]
printf '%s\n' 'funder-weekly-reflection-postgres: PASS replay=2 valid_application=1 missing=blocked tampered=blocked immutable=blocked roles=2'
