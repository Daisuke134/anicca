# CFO-2a2.3c2 Real Provider-to-Local-Ledger E2E Implementation Plan

**Status:** COMPLETE — real gate independently verified before CFO-2a2.4.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Prove that two real Gemini responses become two exactly matching rows in a disposable local ledger and
two content-free exported spans with the same distinct non-zero trace IDs.

**Architecture:** One shell test starts pinned PostgreSQL and PostgREST containers on a disposable Docker network,
applies the two existing migrations, calls the existing exported `agentSearchCandidate`, then reads the table through
PostgREST. One test-local `fetch` wrapper clones Gemini responses without changing them and removes `/rest/v1` only
from requests to the disposable PostgREST host; production code and endpoints remain unchanged.

**Tech Stack:** Bash, Docker, PostgreSQL 18, PostgREST 16.0, Node 20.6+, built-in `fetch`/`assert`/`crypto`.

## Global Constraints

- Luna owns the test file and implementation commands. Sol owns review, real execution, closure, commit, and push.
- Create exactly `apps/life-call/test/postgres/cfo-provider-usage-real-e2e.sh`; change no production or package file.
- Soft target: one file and at most 100 additions. Exceeding either limit means reduce the harness, not raise it.
- Use exact images `postgres:18-alpine` and `postgrest/postgrest:v16.0`; add no Compose file or dependency.
- Use only `agentSearchCandidate`, the two existing migrations, and PostgREST's existing HTTP boundary.
- Require `GEMINI_API_KEY` from the environment. Never echo it, store it, put it in a URL, or write it to a file.
- Set `JWT_SECRET` exactly to `cfo-provider-e2e-jwt-secret-32-bytes` and assert its length is at least 32 characters.
- No fake/mock/dry provider response, production database, production Telegram, scheduler, launchd, or cloud mutation.
- Success requires exactly two real Gemini response IDs and two rows; unknown or missing is failure, never zero.

---

### Task 1: Real Gemini response to disposable ledger proof

**Files:**
- Create: `apps/life-call/test/postgres/cfo-provider-usage-real-e2e.sh`

**Interfaces:**
- Consumes: `agentSearchCandidate(event, deps)`, `GEMINI_API_KEY`,
  `migrations/2026-08-10-cfo-model-usage-evidence.sql`, and
  `migrations/2026-08-10-cfo-model-usage-evidence-append-rpc.sql`.
- Produces: exit `0` plus exactly `cfo-provider-usage-real-e2e: PASS rows=2 spans=2`; any other state exits non-zero.

- [ ] **Step 1: Establish the no-harness baseline**

Run from `apps/life-call`:

```bash
test ! -e test/postgres/cfo-provider-usage-real-e2e.sh
```

Expected: exit `0`. This slice adds only a verification harness, not production behavior, so do not invent a fake
RED unit test for the test itself.

- [ ] **Step 2: Write the minimum hermetic shell boundary**

Start with `set -euo pipefail`; require `GEMINI_API_KEY`, `docker`, `psql`, `curl`, and `node`. Create one `mktemp -d`
directory and names suffixed with `$$`. The cleanup trap stops exactly both named containers, removes exactly the
named Docker network, and removes exactly the validated temporary directory. Start PostgreSQL first and redirect
container/network IDs to `/dev/null`:

```bash
docker network create "$NETWORK" >/dev/null
docker run --rm -d --name "$PG_NAME" --network "$NETWORK" \
  -e POSTGRES_PASSWORD=cfo-e2e-only -e POSTGRES_DB=cfo_provider_e2e \
  -p 127.0.0.1::5432 postgres:18-alpine >/dev/null
```

Resolve the PostgreSQL dynamic host port with `docker port` and a bounded readiness loop. Never use fixed host ports.

- [ ] **Step 3: Apply only the real schema and RPC**

Through host `psql`, create only `anon`, `authenticated`, `service_role`, `authenticator`, `public.lm_users`, and one
`cfo-e2e-owner` row. Grant `service_role` to `authenticator`, then apply both existing migration files unchanged:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE ROLE authenticator LOGIN NOINHERIT PASSWORD 'cfo-e2e-only';
GRANT service_role TO authenticator;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('cfo-e2e-owner');
```

Only after all SQL succeeds, start PostgREST and wait for its dynamic host port and HTTP readiness:

```bash
docker run --rm -d --name "$REST_NAME" --network "$NETWORK" \
  -e PGRST_DB_URI=postgres://authenticator:cfo-e2e-only@"$PG_NAME":5432/cfo_provider_e2e \
  -e PGRST_DB_ANON_ROLE=anon -e PGRST_JWT_SECRET="$JWT_SECRET" \
  -p 127.0.0.1::3000 postgrest/postgrest:v16.0 >/dev/null
```

- [ ] **Step 4: Generate one test-only service-role JWT without a dependency**

Use Node `crypto.createHmac('sha256', JWT_SECRET)` with base64url header
`{"alg":"HS256","typ":"JWT"}` and payload `{"role":"service_role"}`. Keep the token only in an environment
variable passed to the embedded Node process. Do not print it.

- [ ] **Step 5: Call the real existing flow and compare provider truth to stored truth**

Before requiring `ask.js`, retain native `fetch` and intercept `console.log`/`console.dir` into one in-memory exporter
string. Replace `global.fetch` with a wrapper that (a) forwards Gemini requests unchanged and stores
`response.clone().json()`, and (b) removes the exact `/rest/v1` prefix only when the URL origin equals
`CFO_E2E_URL`. This adapter is passed through `storeOptions.fetchImpl`; no production URL is rewritten. Call:

```js
await agentSearchCandidate({
  summary: "Tokyo International Forum venue",
  description: process.env.CFO_E2E_SENTINEL,
}, {
  geminiKey: process.env.GEMINI_API_KEY,
  providerUsage: {
    owner_id: "cfo-e2e-owner",
    financial_unit_id: "life_manager_saas",
    request_model: "gemini-2.5-flash",
    storeOptions: {
      supaUrl: process.env.CFO_E2E_URL,
      supaKey: process.env.CFO_E2E_JWT,
      fetchImpl: localPostgrestFetch,
    },
  },
  mailAvailable: async () => false,
  mail: { ready: () => false, searchInbox: async () => [] },
});
```

Read all two rows directly from PostgREST `/lm_cfo_model_usage_evidence` using the same Bearer token. Sort both sides
by `provider_request_id + usage_sequence`; never depend on response order. With literal field mappings, assert:

```js
assert.equal(providerResponses.length, 2);
assert.equal(rows.length, 2);
assert.deepEqual(rows.map(projectRow), providerResponses.map(projectGeminiUsage));
assert.ok(rows.every(row => /^(?!0{32})[0-9a-f]{32}$/.test(row.trace_id)));
assert.equal(new Set(rows.map(row => row.trace_id)).size, 2);
assert.ok(!JSON.stringify(rows).includes(process.env.CFO_E2E_SENTINEL));
```

`projectGeminiUsage` maps `responseId`, `modelVersion`, `promptTokenCount`, `candidatesTokenCount`,
`totalTokenCount`, and optional cached/thought/tool counts directly; absent optional counts map to `null`. It also
asserts provider `gcp.gemini`, request model `gemini-2.5-flash`, sequence `0`, and status `provider_reported`. Write
only both trace IDs to a temporary trace file.

- [ ] **Step 6: Prove the exported spans correlate and contain no content**

For each trace ID, require exactly one matching entry in the intercepted real `ConsoleSpanExporter` output. Extract
all non-empty provider `text`, function-call names, and string function-argument values from both cloned responses;
require at least one provider text value and reject every extracted value of 12+ characters from exporter output.
Also reject the private input sentinel and exact `GEMINI_API_KEY` value. Restore console functions, write no captured
content, and print only the closed PASS line through `process.stdout.write`.

- [ ] **Step 7: Execute the real gate**

Run from `apps/life-call` after dependencies are installed:

```bash
npm ci
bash -n test/postgres/cfo-provider-usage-real-e2e.sh
env -i PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" \
  GEMINI_API_KEY="$(node --env-file=/Users/anicca/.openclaw/.env -p 'process.env.GEMINI_API_KEY')" \
  test/postgres/cfo-provider-usage-real-e2e.sh
git diff --check
```

Expected: real E2E prints exactly `cfo-provider-usage-real-e2e: PASS rows=2 spans=2`; syntax and diff checks exit `0`.
Return the exact provider-response count, row count, trace count, scope, and any concern to Sol. Do not commit/push.

## Plan self-review

- Coverage: real provider, real PostgREST/RPC/table readback, exact counts, trace correlation, and content exclusion
  are all in Task 1.
- Scope: one test file; no production/package/database/Telegram change.
- Placeholders: none. Exact images, roles, owner, models, commands, paths, output, and failure conditions are fixed.

## Completion evidence

- Luna created one executable 90-line file; no production/package/migration/Compose/proxy file changed.
- The env-isolated real gate returned exactly `cfo-provider-usage-real-e2e: PASS rows=2 spans=2`.
- Fresh Sol review: Spec compliant, Approved, Critical 0, Important 0, Minor 0.
- Fresh Sol execution: `npm ci`, `bash -n`, real E2E, and `git diff --check` all exited `0`.
- No production database, Telegram, scheduler, launchd, or cloud state was mutated.
