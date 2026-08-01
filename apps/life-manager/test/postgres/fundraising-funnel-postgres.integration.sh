#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SUBMISSION="$ROOT_DIR/migrations/2026-08-02-lm-funder-submission-ledger.sql"
RESULT="$ROOT_DIR/migrations/2026-08-02-lm-outbound-result-ledger.sql"
FUNNEL="$ROOT_DIR/migrations/2026-08-02-lm-panel-fundraising-funnel.sql"
DB_NAME="fundraising_funnel_test"
DOCKER_NAME="fundraising-funnel-pg-$$"

cleanup() { docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

export PGPASSWORD="fundraising-funnel-test-only"
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
SQL
"${PSQL[@]}" -f "$SUBMISSION" >/dev/null
"${PSQL[@]}" -f "$RESULT" >/dev/null
"${PSQL[@]}" -f "$FUNNEL" >/dev/null
"${PSQL[@]}" -f "$FUNNEL" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_funder_submission_ledger (
  tenant_id,ledger_id,funder_id,draft_id,application_url,status,provider_status,
  submitted_at,home_observed_at,mail_message_id,mail_thread_id,mail_sender,
  mail_subject,mail_auth,evidence_digest
) VALUES
('tenant-a','funder-ledger:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
 'yc-fall-2026','0b61fe42-e383-490d-b60e-04f1ad7ec5df','https://apply.ycombinator.com/home',
 'submitted','in_review','2026-08-01T01:00:00Z','2026-08-01T01:01:00Z',
 '19fa000000000001','19fa000000000001','apply@ycombinator.com',
 'YC Fall 2026 Application Submitted','{"dkim":true,"spf":true,"dmarc":true}',repeat('a',64)),
('tenant-b','funder-ledger:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
 'yc-fall-2026','1b61fe42-e383-490d-b60e-04f1ad7ec5df','https://apply.ycombinator.com/home',
 'submitted','in_review','2026-08-01T01:00:00Z','2026-08-01T01:01:00Z',
 '19fb000000000001','19fb000000000001','apply@ycombinator.com',
 'YC Fall 2026 Application Submitted','{"dkim":true,"spf":true,"dmarc":true}',repeat('b',64));

INSERT INTO public.lm_outbound_result_ledger (
 tenant_id,result_id,organ,workflow,source_kind,source_id,source_fence,entity_id,
 result_type,status,provider_message_id,provider_thread_id,occurred_at,
 sender_sha256,subject_sha256,body_sha256,message_sha256,evidence_sha256,rationale_sha256
) VALUES
('tenant-a','outbound-result:1000000000000000000000000000000000000000000000000000000000000001','fundraising','funder_application','funder_submission','funder-ledger:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1,'yc-fall-2026','confirmation','confirmed','19fa000000000001','19fa000000000001','2026-08-01T01:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64)),
('tenant-a','outbound-result:1000000000000000000000000000000000000000000000000000000000000002','fundraising','funder_application','funder_submission','funder-ledger:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1,'yc-fall-2026','reply','meeting_requested','19fa000000000002','19fa000000000001','2026-08-01T02:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64)),
('tenant-a','outbound-result:1000000000000000000000000000000000000000000000000000000000000003','fundraising','funder_application','funder_submission','funder-ledger:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1,'yc-fall-2026','reply','offer_received','19fa000000000003','19fa000000000001','2026-08-01T03:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64)),
('tenant-a','outbound-result:1000000000000000000000000000000000000000000000000000000000000004','fundraising','funder_application','funder_submission','funder-ledger:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1,'yc-fall-2026','reply','funded','19fa000000000004','19fa000000000001','2026-08-01T04:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64)),
('tenant-b','outbound-result:2000000000000000000000000000000000000000000000000000000000000001','fundraising','funder_application','funder_submission','funder-ledger:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',1,'yc-fall-2026','confirmation','confirmed','19fb000000000001','19fb000000000001','2026-08-01T01:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64)),
('tenant-b','outbound-result:2000000000000000000000000000000000000000000000000000000000000002','fundraising','funder_application','funder_submission','funder-ledger:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',1,'yc-fall-2026','reply','rejected','19fb000000000002','19fb000000000001','2026-08-01T02:00:00Z',repeat('1',64),repeat('2',64),repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64));
SQL

A_JSON="$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_fundraising_funnel('tenant-a');")"
B_JSON="$("${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT public.lm_panel_fundraising_funnel('tenant-b');")"
[[ "$(jq -r '.schema_version' <<<"$A_JSON")" == "1" ]]
[[ "$(jq -r '.events | length' <<<"$A_JSON")" == "5" ]]
[[ "$(jq -r '[.events[].event_kind] | join(",")' <<<"$A_JSON")" == "application,confirmation,interview,offer,funded" ]]
[[ "$(jq -r '.events | length' <<<"$B_JSON")" == "3" ]]
[[ "$(jq -r '[.events[].event_kind] | join(",")' <<<"$B_JSON")" == "application,confirmation,rejected" ]]
[[ "$(jq -r '[.events[].source_id] | unique | length' <<<"$A_JSON")" == "1" ]]
[[ "$(jq -r '.events[0] | keys | join(",")' <<<"$A_JSON")" == "event_kind,funder_id,occurred_at,source_id" ]]

for role in anon authenticated; do
  if "${PSQL[@]}" -c "SET ROLE ${role}; SELECT public.lm_panel_fundraising_funnel('tenant-a');" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} executed funnel RPC" >&2
    exit 1
  fi
done
printf '%s\n' 'fundraising-funnel-postgres: PASS replay=2 tenants=2 events=8 roles=3'
