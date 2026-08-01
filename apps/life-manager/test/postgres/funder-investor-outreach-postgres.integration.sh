#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTREACH="$ROOT_DIR/migrations/2026-08-02-lm-funder-outreach-ledger.sql"
INVESTOR="$ROOT_DIR/migrations/2026-08-02-lm-funder-investor-outreach.sql"
DB_NAME="funder_investor_outreach_test"
DOCKER_NAME="funder-investor-outreach-pg-$$"

cleanup() { docker stop "$DOCKER_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

export PGPASSWORD="funder-investor-outreach-test-only"
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

-- Exact pre-O1C-19 shape: the new migration must upgrade this table by itself.
CREATE TABLE public.lm_funder_outreach_ledger (
  tenant_id text NOT NULL,
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  batch_id text NOT NULL CHECK (batch_id ~ '^funder-outreach-batch:[0-9a-f]{64}$'),
  tokyo_date date NOT NULL,
  candidate_id text NOT NULL,
  funder_name text NOT NULL,
  recipient_sha256 text NOT NULL CHECK (recipient_sha256 ~ '^[0-9a-f]{64}$'),
  source_url text NOT NULL CHECK (source_url ~ '^https://'),
  source_observed_at timestamptz NOT NULL,
  source_digest text NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
  fit_summary_sha256 text NOT NULL CHECK (fit_summary_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 text NOT NULL CHECK (subject_sha256 ~ '^[0-9a-f]{64}$'),
  body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
  sent_at timestamptz NOT NULL,
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id,outreach_id),
  UNIQUE (tenant_id,recipient_sha256),
  UNIQUE (tenant_id,provider_message_id)
);
SQL
"${PSQL[@]}" -f "$INVESTOR" >/dev/null
"${PSQL[@]}" -f "$OUTREACH" >/dev/null
"${PSQL[@]}" -f "$INVESTOR" >/dev/null

"${PSQL[@]}" >/dev/null <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger (
 tenant_id,outreach_id,batch_id,tokyo_date,candidate_id,funder_name,recipient_sha256,
 source_url,source_observed_at,source_digest,fit_summary_sha256,subject_sha256,body_sha256,
 sent_at,provider_message_id,provider_thread_id
) SELECT
 'tenant-a','funder-outreach:'||repeat(to_hex(n),64),'funder-outreach-batch:'||repeat('a',64),
 '2026-08-02','old-'||n,'Old '||n,repeat(to_hex(n+3),64),'https://example.com',
 '2026-08-01T20:00:00Z',repeat('b',64),repeat('c',64),repeat('d',64),repeat('e',64),
 ('2026-08-01T20:0'||n||':00Z')::timestamptz,'19fa00000000000'||n,'19fa00000000000'||n
FROM generate_series(1,3) n;
SQL

reserve() {
  local tenant="$1" date="$2" digit="$3"
  "${PSQL[@]}" -Atqc "SET ROLE service_role; SELECT daily_slot FROM public.lm_reserve_funder_investor_outreach(
    '$tenant','$date','funder-outreach:$(printf "%064d" "$digit")',repeat('f',63)||'$digit','vc',repeat('1',64),repeat('2',64),repeat('3',64));"
}

RACE_DIR="$(mktemp -d)"
for digit in 4 5 6; do
  (
    if reserve tenant-a 2026-08-02 "$digit" >"$RACE_DIR/$digit.out" 2>"$RACE_DIR/$digit.err"; then
      printf '0\n' >"$RACE_DIR/$digit.status"
    else
      printf '1\n' >"$RACE_DIR/$digit.status"
    fi
  ) &
done
wait
SUCCESS="$(awk '$1==0{n++} END{print n+0}' "$RACE_DIR"/*.status)"
[[ "$SUCCESS" == "2" ]]
SLOTS="$(cat "$RACE_DIR"/*.out | sort -n | paste -sd, -)"
[[ "$SLOTS" == "4,5" ]]
WIN4="$(basename "$(grep -l '^4$' "$RACE_DIR"/*.out)" .out)"
WIN5="$(basename "$(grep -l '^5$' "$RACE_DIR"/*.out)" .out)"
SLOT="$(reserve tenant-a 2026-08-03 9)"; [[ "$SLOT" == "1" ]]
SLOT="$(reserve tenant-b 2026-08-02 6)"; [[ "$SLOT" == "1" ]]
SLOT="$(reserve tenant-c 2026-08-04 8)"; [[ "$SLOT" == "1" ]]
SLOT="$(reserve tenant-c 2026-08-04 8)"; [[ "$SLOT" == "1" ]]

"${PSQL[@]}" -v winner4="$WIN4" >/dev/null <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger (
 tenant_id,outreach_id,batch_id,tokyo_date,candidate_id,funder_name,recipient_sha256,
 source_url,source_observed_at,source_digest,fit_summary_sha256,subject_sha256,body_sha256,
 sent_at,provider_message_id,provider_thread_id,investor_kind,thesis_evidence_sha256,
 company_evidence_sha256,personalization_sha256,daily_slot
) VALUES (
 'tenant-a','funder-outreach:'||lpad(:'winner4',64,'0'),'funder-outreach-batch:'||repeat('4',64),
 '2026-08-02','investor-4','Investor 4',repeat('f',63)||:'winner4','https://example.com/investor',
 '2026-08-01T21:00:00Z',repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),
 '2026-08-01T21:01:00Z','19fa000000000004','19fa000000000004','vc',repeat('1',64),repeat('2',64),repeat('3',64),4
);
SQL

if "${PSQL[@]}" -v winner5="$WIN5" >/dev/null 2>&1 <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger (
 tenant_id,outreach_id,batch_id,tokyo_date,candidate_id,funder_name,recipient_sha256,
 source_url,source_observed_at,source_digest,fit_summary_sha256,subject_sha256,body_sha256,
 sent_at,provider_message_id,provider_thread_id,investor_kind,thesis_evidence_sha256,
 company_evidence_sha256,personalization_sha256,daily_slot
) VALUES (
 'tenant-a','funder-outreach:'||repeat('7',64),'funder-outreach-batch:'||repeat('7',64),
 '2026-08-02','unreserved','Unreserved',repeat('6',64),'https://example.com/unreserved',
 '2026-08-01T21:00:00Z',repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),
 '2026-08-01T21:02:00Z','19fa000000000007','19fa000000000007','vc',repeat('1',64),repeat('2',64),repeat('3',64),5
);
SQL
then
  printf '%s\n' 'FAIL unreserved investor receipt inserted' >&2
  exit 1
fi

if "${PSQL[@]}" >/dev/null 2>&1 <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger (
 tenant_id,outreach_id,batch_id,tokyo_date,candidate_id,funder_name,recipient_sha256,
 source_url,source_observed_at,source_digest,fit_summary_sha256,subject_sha256,body_sha256,
 sent_at,provider_message_id,provider_thread_id,investor_kind,thesis_evidence_sha256,
 company_evidence_sha256,personalization_sha256,daily_slot
) VALUES (
 'tenant-a','funder-outreach:'||lpad(:'winner5',64,'0'),'funder-outreach-batch:'||repeat('5',64),
 '2026-08-02','wrong-proof','Wrong Proof',repeat('f',63)||:'winner5','https://example.com/wrong-proof',
 '2026-08-01T21:00:00Z',repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),
 '2026-08-01T21:03:00Z','19fa000000000005','19fa000000000005','vc',repeat('9',64),repeat('2',64),repeat('3',64),5
);
SQL
then
  printf '%s\n' 'FAIL mismatched reservation proof inserted' >&2
  exit 1
fi

if "${PSQL[@]}" >/dev/null 2>&1 <<'SQL'
INSERT INTO public.lm_funder_outreach_ledger (
 tenant_id,outreach_id,batch_id,tokyo_date,candidate_id,funder_name,recipient_sha256,
 source_url,source_observed_at,source_digest,fit_summary_sha256,subject_sha256,body_sha256,
 sent_at,provider_message_id,provider_thread_id,investor_kind
) VALUES (
 'tenant-z','funder-outreach:'||repeat('a',64),'funder-outreach-batch:'||repeat('a',64),
 '2026-08-02','partial','Partial',repeat('b',64),'https://example.com/partial',
 '2026-08-01T21:00:00Z',repeat('c',64),repeat('d',64),repeat('e',64),repeat('f',64),
 '2026-08-01T21:04:00Z','19fa00000000000a','19fa00000000000a','vc'
);
SQL
then
  printf '%s\n' 'FAIL partial investor proof inserted' >&2
  exit 1
fi

if "${PSQL[@]}" >/dev/null 2>&1 <<'SQL'
SET ROLE service_role;
INSERT INTO public.lm_funder_investor_outreach_reservation (
 tenant_id,outreach_id,tokyo_date,recipient_sha256,investor_kind,
 thesis_evidence_sha256,company_evidence_sha256,personalization_sha256,daily_slot
) VALUES (
 'tenant-z','funder-outreach:'||repeat('9',64),'2026-08-02',repeat('8',64),'angel',
 repeat('1',64),repeat('2',64),repeat('3',64),1
);
SQL
then
  printf '%s\n' 'FAIL service_role bypassed reservation RPC' >&2
  exit 1
fi

for role in anon authenticated; do
  if "${PSQL[@]}" -c "SET ROLE ${role}; SELECT * FROM public.lm_reserve_funder_investor_outreach(
    'tenant-x','2026-08-02','funder-outreach:'||repeat('9',64),repeat('8',64),'angel',repeat('1',64),repeat('2',64),repeat('3',64));" >/dev/null 2>&1; then
    printf '%s\n' "FAIL ${role} executed investor reservation" >&2
    exit 1
  fi
done

if "${PSQL[@]}" -c "SET ROLE service_role; SELECT * FROM public.lm_reserve_funder_investor_outreach(
  'tenant-null','2026-08-02','funder-outreach:'||repeat('9',64),NULL,'angel',repeat('1',64),repeat('2',64),repeat('3',64));" >/dev/null 2>&1; then
  printf '%s\n' 'FAIL null reservation input accepted' >&2
  exit 1
fi

COUNT="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_funder_investor_outreach_reservation")"
[[ "$COUNT" == "5" ]]
MATCHED="$("${PSQL[@]}" -Atqc "SELECT count(*) FROM public.lm_funder_outreach_ledger WHERE investor_kind='vc' AND daily_slot=4")"
[[ "$MATCHED" == "1" ]]
printf '%s\n' 'funder-investor-outreach-postgres: PASS legacy_upgrade=1 replay=2 old=3 concurrent=3 success=2 cap=5 receipt_fk=1 proof_fk=1 partial_null=blocked null_input=blocked direct_insert=blocked dates=4 tenants=3 roles=3'
