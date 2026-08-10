# CFO-2a2.4a Gemini Live Provenance Schema Implementation Plan

**Status:** COMPLETE — verified and ready for CFO-2a2.4b.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the existing CFO usage-evidence table store Gemini Live provider token counts without inventing a provider response ID or response model.

**Architecture:** Add one forward PostgreSQL migration. Reuse the existing table, privacy boundary, provider unique constraint, and real-provider E2E; distinguish the local Live correlation path with one nullable column, one XOR-style check, and one partial unique index.

**Tech Stack:** PostgreSQL 18 SQL, Node built-in `node:test`, Bash, existing Docker/PostgREST real E2E.

## Global Constraints

- Luna owns production/test code and implementation commands. Sol owns review, final verification, closure, commit, and push.
- Modify exactly the three files listed below; add at most 70 lines total.
- Add no dependency, table, RPC/function, policy/grant, Node production code, WebSocket, span, scheduler, launchd, Telegram behavior, content, raw response, metadata JSON, price, or billing field.
- Preserve every existing row and the existing GenerateContent provider append path without a backfill.
- `provider_request_id` and `response_model` mean provider-returned facts only; `local_correlation_id` means local identity only.
- Run every command from `apps/life-call` inside the CFO worktree.

---

### Task 1: Add the truthful Live provenance path

**Files:**
- Create: `apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence-live-provenance.sql`
- Modify: `apps/life-call/lib/cfo-model-usage-evidence-migration.test.js`
- Modify: `apps/life-call/test/postgres/cfo-provider-usage-real-e2e.sh`

**Interfaces:**
- Consumes: the existing `public.lm_cfo_model_usage_evidence` table and unchanged provider append RPC.
- Produces: nullable `local_correlation_id text`, nullable provider response ID/model, a named exclusive identity-path check, and a local-identity partial unique index.

- [x] **Step 1: Write the failing static migration contract test**

Add `liveProvenanceMigrationPath`, read the new SQL in one focused test, and require these exact semantics:

```text
ADD COLUMN local_correlation_id text
ALTER COLUMN provider_request_id DROP NOT NULL
ALTER COLUMN response_model DROP NOT NULL
local_correlation_id IS NULL OR local_correlation_id ~ '^live-session:[0-9a-f]{32}$'
provider path = provider_request_id non-null + response_model non-null + local_correlation_id null
local path = provider_request_id null + response_model null + local_correlation_id non-null
UNIQUE (provider, local_correlation_id, usage_sequence) WHERE local_correlation_id IS NOT NULL
```

Assert the file has no `UPDATE`, `DELETE`, backfill, content/raw-response/metadata/JSON field, function/RPC,
policy/grant/revoke, or base-table recreation.

- [x] **Step 2: Run RED**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
```

Expected: exactly one new test fails with `ENOENT` for the missing forward migration; the two existing tests pass.

- [x] **Step 3: Add the minimum forward migration**

Create one `ALTER TABLE` plus one index:

```sql
ALTER TABLE public.lm_cfo_model_usage_evidence
  ADD COLUMN local_correlation_id text
    CONSTRAINT lm_cfo_model_usage_evidence_local_correlation_format
    CHECK (local_correlation_id IS NULL OR local_correlation_id ~ '^live-session:[0-9a-f]{32}$'),
  ALTER COLUMN provider_request_id DROP NOT NULL,
  ALTER COLUMN response_model DROP NOT NULL,
  ADD CONSTRAINT lm_cfo_model_usage_evidence_identity_path_check CHECK (
    (provider_request_id IS NOT NULL AND response_model IS NOT NULL AND local_correlation_id IS NULL)
    OR
    (provider_request_id IS NULL AND response_model IS NULL AND local_correlation_id IS NOT NULL)
  );

CREATE UNIQUE INDEX lm_cfo_model_usage_evidence_local_identity_unique
  ON public.lm_cfo_model_usage_evidence (provider, local_correlation_id, usage_sequence)
  WHERE local_correlation_id IS NOT NULL;
```

Do not modify the base migration or append RPC.

- [x] **Step 4: Extend the existing real-provider E2E**

Apply the forward migration after the base and RPC migrations and before PostgREST starts. In a rolled-back SQL
transaction, insert one valid Live-shaped row with provider response ID/model null and
`local_correlation_id = 'live-session:' || repeat('2', 32)`. Prove a mixed row with both provider and local IDs is
rejected by `lm_cfo_model_usage_evidence_identity_path_check`, and prove a duplicate local
`(provider, local_correlation_id, usage_sequence)` is rejected by
`lm_cfo_model_usage_evidence_local_identity_unique`. Prove `live-session:not-hex` is rejected by
`lm_cfo_model_usage_evidence_local_correlation_format`.

Keep the existing real Gemini request and exact final output. Add `local_correlation_id` to the read projection and
assert both real GenerateContent rows retain non-empty provider IDs/models and have `local_correlation_id === null`.

- [x] **Step 5: Run GREEN and scope gates**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
bash -n test/postgres/cfo-provider-usage-real-e2e.sh
env -i PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" \
  GEMINI_API_KEY="$(node --env-file=/Users/anicca/.openclaw/.env -p 'process.env.GEMINI_API_KEY')" \
  test/postgres/cfo-provider-usage-real-e2e.sh
npm run test:cfo
npm test
git add -N migrations/2026-08-10-cfo-model-usage-evidence-live-provenance.sql
git diff --check -- \
  migrations/2026-08-10-cfo-model-usage-evidence-live-provenance.sql \
  lib/cfo-model-usage-evidence-migration.test.js \
  test/postgres/cfo-provider-usage-real-e2e.sh
git diff --numstat -- \
  migrations/2026-08-10-cfo-model-usage-evidence-live-provenance.sql \
  lib/cfo-model-usage-evidence-migration.test.js \
  test/postgres/cfo-provider-usage-real-e2e.sh \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 3 && added <= 70) }'
```

Expected: every command exits `0`; the real E2E ends exactly
`cfo-provider-usage-real-e2e: PASS rows=2 spans=2`; exactly three implementation files change with at most 70 added
lines. Sol separately rejects any unplanned path in the whole worktree. Return RED/GREEN totals and concerns to Sol.
Do not commit or push.

## Plan self-review

- Coverage: truthful identity paths, migration safety, local uniqueness, mixed-path rejection, and provider-path regression.
- Scope: one forward migration and two reused tests; no new runtime surface.
- Placeholders: none. Column, constraint, index, values, commands, limits, and expected output are fixed.

## Completion evidence

- RED: 2/3 passed; only the missing forward migration failed with `ENOENT`.
- GREEN: focused 3/3, CFO 264/264, full `npm test` exit `0`.
- Real gate: `cfo-provider-usage-real-e2e: PASS rows=2 spans=2`.
- Scope: exactly three implementation files and 65 additions; diff and shell syntax checks passed.
- Fresh Sol implementation review: `ship`.
- No production database or Telegram mutation occurred.
