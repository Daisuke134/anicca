# Life Manager CFO-2a2.2b Provider Usage Append RPC Plan

**Status:** READY — one Luna task; RPC boundary only.

> **Executor:** Luna uses Superpowers subagent-driven development with strict RED → minimal GREEN → disposable
> PostgreSQL E2E. Sol owns this plan, final verification, closure, and push.

**Goal:** Append one already-normalized provider-usage fact exactly once and return one privacy-safe receipt.

**Architecture:** One forward SQL migration adds one typed invoker-security RPC over the verified 2a2.2a table.
The existing migration contract test gains focused assertions. No client, provider call, SDK, span, scheduler, or
production apply is included.

**Tech stack:** PostgreSQL 18 PL/pgSQL; Node.js built-in `node:test`; no dependency or package-script change.

## Ponytail gate

- Reuse `lm_cfo_model_usage_evidence`, its named unique constraint, RLS, grants, and existing test.
- Add one migration; modify one test. Soft target: 60–70 SQL LOC + 20–25 test LOC, 95 additions total.
- No JSON/JSONB input or stored evidence, UPDATE, advisory lock, new table/index/trigger/policy, helper function,
  client, retry loop, content, metadata, price, billing, OTel SDK/exporter, Gemini wiring, launchd, or
  production/remote DB command. The closed receipt is the only JSON return.
- Test only wrong-money, duplicate-write, mutation, tenant execution, and secret/content exposure boundaries.

## Task 1 — Add the idempotent typed append RPC

**Files**

- Create: `apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence-append-rpc.sql`
- Modify: `apps/life-call/lib/cfo-model-usage-evidence-migration.test.js`

- [ ] **Step 1 — Write the focused static contract RED**

Extend the existing test to read the forward migration and prove:

- exactly one function named `public.lm_append_cfo_model_usage_evidence`;
- the exact 17 typed scalar arguments and `RETURNS jsonb` interface below; no JSON/JSONB argument;
- `SECURITY INVOKER`, fixed `search_path = public, pg_temp`;
- insert into the exact 17 columns with `ON CONFLICT ON CONSTRAINT
  lm_cfo_model_usage_evidence_identity_unique DO NOTHING` before lookup;
- lookup by exact provider/request/sequence identity and null-safe comparison of all 17 fields;
- fixed `provider_usage_identity_conflict`, no UPDATE/DELETE, no dynamic SQL;
- one explicit six-key `jsonb_build_object` receipt and no owner/unit/token/model fields in it;
- revoke-all for PUBLIC/anon/authenticated/service_role, then execute grant only to service_role.

Run `node --test lib/cfo-model-usage-evidence-migration.test.js`. Expected RED: the existing schema test passes and
the new RPC test fails only because the forward migration does not exist.

- [ ] **Step 2 — Add the minimal forward migration**

Use this exact ordered interface:

```sql
public.lm_append_cfo_model_usage_evidence(
  p_uid text, p_financial_unit_id text, p_attribution_status text,
  p_provider text, p_provider_request_id text, p_usage_sequence bigint,
  p_occurred_at timestamptz, p_trace_id text, p_request_model text, p_response_model text,
  p_input_tokens bigint, p_output_tokens bigint, p_total_tokens bigint,
  p_cached_input_tokens bigint, p_reasoning_output_tokens bigint, p_tool_input_tokens bigint,
  p_evidence_status text
) RETURNS jsonb
```

Attempt the insert first and store `RETURNING *`. On conflict, select the existing row by the three-part identity.
Use one null-safe row comparison covering every supplied field. Exact match returns the stored receipt; any missing
or different row raises only `provider_usage_identity_conflict` with SQLSTATE `23505`. Return the same literal
six-key projection for first insert and retry. The fixed conflict guarantee applies only when all 17 proposed values
independently satisfy the existing table constraints; invalid input remains a schema error. Never update.

- [ ] **Step 3 — Run focused and repository GREEN**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
npm run test:cfo
npm test
```

Expected: focused 2/2; CFO 256/256; full aggregate 894/894, all failures zero.

- [ ] **Step 4 — Run disposable PostgreSQL E2E**

In a fresh local PostgreSQL 18 instance, create only synthetic roles/users, apply the 2a2.2a schema then this
forward migration, and prove:

1. service_role first call inserts one row and returns exactly the six receipt keys;
2. exact retry returns the identical receipt and row count remains one;
3. same identity with changed owner (an existing synthetic `tenant-b`), total token count, optional NULL→zero, or
   valid trace ID raises the fixed conflict and preserves the first row;
4. use two named PostgreSQL sessions: Session A calls inside an uncommitted transaction; Session B starts the exact
   retry; verify B is waiting on A's unique conflict, then commit A and prove both receipts have one shared
   `public_ref` and the table has one row;
5. anon/authenticated cannot execute; service_role can execute but cannot UPDATE/DELETE the table;
6. neither receipt nor fixed conflict contains owner, unit, model, token count, provider payload, content, or secret.

Do not apply either migration to production or remote Supabase.

- [ ] **Step 5 — Verify Ponytail scope and commit**

Run `git diff --check`, exact-name diff, and numstat. Expected: two tracked files, at most 95 additions. Commit only
those files with `feat(cfo): add idempotent usage append rpc`; do not push. Update the ignored SDD report with RED,
GREEN, PostgreSQL, LOC, and commit evidence. Sol performs fresh review/E2E, closes specs, fetches, and pushes.
