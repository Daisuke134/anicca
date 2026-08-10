# Life Manager CFO-2a2.2a Usage Storage Schema Implementation Plan

**Status:** COMPLETE — schema boundary verified locally; no production apply.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Implement this one task
> with strict RED → minimal GREEN → disposable local PostgreSQL E2E.

**Goal:** Add the smallest private, append-only, deduplicated structured table that can later store the verified
provider-usage record.

**Architecture:** One additive PostgreSQL migration defines the durable invariants. One dedicated static contract
test is added to the existing CFO command. No RPC, Node client, provider call, SDK, exporter, or production apply is
part of this plan.

**Tech Stack:** PostgreSQL 18 SQL, Node.js built-in `node:test`, existing npm scripts; no dependency change.

## Global constraints

- Add exactly:
  - `apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence.sql`
  - `apps/life-call/lib/cfo-model-usage-evidence-migration.test.js`
- Modify only `apps/life-call/package.json` to include the new test in `test:cfo`.
- At most three tracked files and 100 added LOC total: target 65–70 SQL, 25–30 test, one script line.
- Sol owns spec/plan/final verification/push. Luna owns SQL, tests, local PostgreSQL commands, and implementation
  commit.
- No JSON/JSONB evidence blob, raw response, generic metadata, prompt/output content, secret, OTel content
  attribute, price, billing value, RPC, retry behavior, client, call-site, scheduler, or deployment.
- Do not alter an existing table or migration.
- Test only invariants that prevent wrong money, duplicates, mutation, tenant exposure, or content storage.

---

### Task 1: Define the structured append-only evidence table

**Files**

- Create: `apps/life-call/lib/cfo-model-usage-evidence-migration.test.js`
- Create: `apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence.sql`
- Modify: `apps/life-call/package.json`

- [x] **Step 1 — Add the static contract test and test:cfo entry**

The test reads the exact migration path and uses a compact literal pattern table to prove:

- table `public.lm_cfo_model_usage_evidence`;
- identity primary key plus non-zero unique UUID `public_ref`;
- `uid` foreign key to `public.lm_users(uid)`;
- structured identity/model/token/status columns from design §11, with no `json` or `jsonb` type;
- unique `(provider, provider_request_id, usage_sequence)`;
- non-negative required and optional token checks;
- attributed/non-null and unattributed/null equivalence;
- RLS plus service-role SELECT/INSERT policies and grants;
- revoked UPDATE/DELETE and an append-only UPDATE/DELETE trigger;
- fixed search path and invoker security for the trigger function;
- no append RPC in this migration.

Add the test path once to `package.json` `test:cfo`.

- [x] **Step 2 — Run RED**

From `apps/life-call`:

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
```

Expected: one test fails only because the planned migration file does not exist. A syntax error or a different
failure is fixed before SQL is written.

- [x] **Step 3 — Add the minimal migration**

Create one table with these columns:

| Column | Contract |
|---|---|
| `id` | generated identity primary key |
| `public_ref` | non-zero generated UUID, unique |
| `uid` | non-empty owner, FK to `lm_users(uid)` |
| `financial_unit_id` | nullable canonical registry ID matching `^[a-z][a-z0-9_]*$` |
| `attribution_status` | `attributed` or `unattributed`, consistent with financial-unit nullability |
| `provider` | non-empty lower-case dotted ID |
| `provider_request_id` | non-empty trimmed provider identity |
| `usage_sequence` | non-negative integer |
| `occurred_at` | required timestamptz |
| `trace_id` | non-zero 32-lowercase-hex |
| `request_model`, `response_model` | required trimmed text |
| `input_tokens`, `output_tokens`, `total_tokens` | required non-negative bigint |
| `cached_input_tokens`, `reasoning_output_tokens`, `tool_input_tokens` | nullable non-negative bigint |
| `evidence_status` | `provider_reported` or `locally_estimated` |
| `created_at` | `clock_timestamp()` default |

Name the composite unique constraint. Do not assert that total equals component sums.

Enable RLS. Create service-role SELECT and INSERT policies only. Revoke all from PUBLIC/anon/authenticated; grant
service SELECT/INSERT and sequence usage/select; explicitly revoke UPDATE/DELETE. Add one invoker,
fixed-`search_path` trigger function and one BEFORE UPDATE OR DELETE trigger that always raises a fixed error.

- [x] **Step 4 — Run focused and repository GREEN**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
npm run test:cfo
npm test
```

Expected: focused 1/1; CFO 255/255; full aggregate 893/893.

- [x] **Step 5 — Run a disposable local PostgreSQL E2E**

Reuse the bootstrap pattern from `test/postgres/cfo-daily-snapshot-postgres.integration.sh`; do not change that
script. In a fresh `mktemp -d` PostgreSQL cluster:

1. create synthetic `anon`, `authenticated`, `service_role` roles and a minimal `lm_users(uid)`;
2. apply only the new migration;
3. assert table/RLS/policies/grants/unique constraint/trigger exist;
4. as `service_role`, insert one synthetic attributed row with optional NULL counts and one unique row with
   explicit optional zero; read both back;
5. prove the exact duplicate identity, negative count, attribution contradiction, UPDATE, and DELETE are rejected;
6. prove a leading-digit financial-unit ID is rejected;
7. prove anon/authenticated SELECT and INSERT are denied.

Stop the cluster and remove only its generated temp directory. Record only pass/fail facts and synthetic IDs; no
credentials, raw provider response, or private content.

- [x] **Step 6 — Enforce Ponytail scope and commit**

```bash
git diff --check
git diff --numstat -- apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence.sql apps/life-call/lib/cfo-model-usage-evidence-migration.test.js apps/life-call/package.json
git status --short
```

Expected: exact three files, at most 100 additions. Commit only them:

```bash
git add apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence.sql apps/life-call/lib/cfo-model-usage-evidence-migration.test.js apps/life-call/package.json
git commit -m "feat(cfo): add model usage evidence table"
```

Write RED/GREEN/PostgreSQL/LOC/commit evidence to the ignored task report. Do not push. Sol performs focused review,
fresh local PostgreSQL verification, spec closure, fetch, and push.
