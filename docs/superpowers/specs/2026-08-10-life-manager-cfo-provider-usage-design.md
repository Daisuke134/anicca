# Life Manager CFO-2a2 — Provider-Reported Usage and OpenTelemetry Contract

| Field | Value |
|---|---|
| Status | ACTIVE — CFO-2a2.1 through CFO-2a2.2c verified; CFO-2a2.3 real Gemini wiring is next |
| Parent | `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md` |
| Runtime | Existing `apps/life-call` package |
| First provider | Gemini `generateContent` response |
| Role split | Sol plans and verifies; Luna writes production code/tests and runs implementation commands |

## 1. Goal

Turn Gemini's own `GenerateContentResponse.usageMetadata` into one deterministic, content-free usage evidence
record and the matching OpenTelemetry GenAI attributes. OpenTelemetry transports and correlates the facts; Gemini's
response is the source of the token numbers.

This child spec does not call a local tokenizer, infer tokens from duration, price tokens, or relabel existing
`lm_api_cost` estimates as measured.

## 2. Ponytail decision

Three approaches were evaluated:

1. **Chosen — contract first in the existing ledger module.** Add one pure
   `normalizeGeminiUsageEvidence(response, context)` function and two focused tests to the existing
   `ledger.js` / `ledger.test.js`. No dependency, SDK, collector, migration, or call-site changes.
2. Add the full OpenTelemetry SDK, OTLP exporter, database table, and all Gemini wiring now. Rejected because four
   independently failing boundaries would be introduced before the meaning of one token field is proven.
3. Store local tokenizer or duration estimates as measured usage. Rejected because transport does not improve
   evidence quality and this would make the CFO lie.

CFO-2a2.1 changes exactly two existing files. Soft target: at most 45 production additions and 55 test additions,
100 total. Exceeding the target, adding a third file, or adding a dependency means the slice must be reduced.

## 3. Full CFO-2a2 sequence

```mermaid
flowchart LR
    A[2a2.1\nPure provider contract] --> B[2a2.2\nAppend-only usage store]
    B --> C[2a2.3\nReal generateContent wiring]
    C --> D[2a2.4\nGemini Live usage]
    D --> E[Real E2E\nresponse → record → span]

    A -. no SDK/DB .-> A
    E --> DONE[CFO-2a2 complete]
```

CFO-2a2.1 through CFO-2a2.2c are complete. CFO-2a2.3 is the only active slice; later slices cannot be pulled into it.

## 4. CFO-2a2.1 input

`normalizeGeminiUsageEvidence(response, context)` consumes:

- `response.responseId`: non-empty provider response identity.
- `response.modelVersion`: non-empty provider-reported model.
- `response.usageMetadata.promptTokenCount`: non-negative safe integer.
- `response.usageMetadata.candidatesTokenCount`: non-negative safe integer.
- `response.usageMetadata.totalTokenCount`: non-negative safe integer.
- Optional non-negative safe integers: `cachedContentTokenCount`, `thoughtsTokenCount`,
  `toolUsePromptTokenCount`.
- Context: non-empty `owner_id`, exact `financial_unit_id: "life_manager_saas"`, RFC3339 `occurred_at`, exact requested model,
  and a non-zero 32-lowercase-hex `trace_id`.

Unknown response/context keys and all prompt, candidate, tool argument, or output content are ignored.

## 5. Closed output

```json
{
  "schema_version": 1,
  "provider": "gcp.gemini",
  "provider_request_id": "provider-response-id",
  "usage_sequence": 0,
  "occurred_at": "2026-08-10T01:02:03.000Z",
  "owner_id": "u1",
  "financial_unit_id": "life_manager_saas",
  "trace_id": "11111111111111111111111111111111",
  "request_model": "gemini-2.5-flash",
  "response_model": "gemini-2.5-flash-001",
  "tokens": {
    "input": 100,
    "output": 40,
    "cached_input": 20,
    "reasoning_output": 5,
    "tool_input": 3,
    "total": 148
  },
  "evidence_status": "provider_reported",
  "otel_attributes": {
    "gen_ai.operation.name": "generate_content",
    "gen_ai.provider.name": "gcp.gemini",
    "gen_ai.request.model": "gemini-2.5-flash",
    "gen_ai.response.id": "provider-response-id",
    "gen_ai.response.model": "gemini-2.5-flash-001",
    "gen_ai.usage.input_tokens": 100,
    "gen_ai.usage.output_tokens": 45,
    "gen_ai.usage.cache_read.input_tokens": 20,
    "gen_ai.usage.reasoning.output_tokens": 5,
    "server.address": "generativelanguage.googleapis.com",
    "server.port": 443
  }
}
```

`tokens.output` preserves Gemini's `candidatesTokenCount`. OpenTelemetry `output_tokens` includes the separately
reported reasoning count because the pinned GenAI convention says reasoning output is included in output tokens.
The provider's `totalTokenCount` is preserved independently and is not replaced by a locally recomputed total.
Missing optional provider fields become `null` in `tokens` and are omitted from `otel_attributes`; an explicit
provider zero remains zero. Because `server.address` is emitted, the pinned OpenTelemetry convention also requires
`server.port: 443` for the HTTPS endpoint.

## 6. Evidence and privacy rules

- `provider_reported` is allowed only when the exact provider response contains usage metadata and response ID.
- Duration-derived `gemini_live` rows remain `locally_estimated`; CFO-2a2 never backfills them as measured.
- The adapter is pure, deterministic, does not mutate inputs, and performs no I/O.
- Invalid or unsafe values throw only `cfo_provider_usage_invalid:<reason>`. Errors contain no IDs, token values,
  prompt text, candidate text, metadata, or secrets.
- No content-bearing OpenTelemetry attributes are emitted: no `gen_ai.input.messages`,
  `gen_ai.output.messages`, `gen_ai.system_instructions`, or tool arguments/results.

## 7. Acceptance criteria for CFO-2a2.1

- [x] One literal Gemini response maps to the exact closed record and exact OpenTelemetry attributes.
- [x] The record preserves provider input, candidate output, cached, reasoning, tool, and total counts without
      converting an absent count to zero.
- [x] The OpenTelemetry output count includes reported reasoning and fails on unsafe integer addition.
- [x] Provider response ID, requested model, response model, owner, fixed Life Manager financial unit, timestamp, and trace ID are
      validated; failures are fixed and redacted.
- [x] Unknown keys and content-shaped fields never enter the result or errors.
- [x] Inputs remain unchanged; repeated calls return deep-equal results.
- [x] Focused ledger tests and the CFO suite pass.

## 8. Deferred completion gates

CFO-2a2 remains unchecked in the parent until later child slices prove:

1. append-only deduplicated storage keyed by `(provider, provider_request_id, usage_sequence)`;
2. a real Gemini `generateContent` response writes one evidence record and correlates one actual span;
3. Gemini Live terminal `usageMetadata` is captured without relabeling historic duration estimates;
4. real readback shows no prompt/output content and exact provider token counts.

Write-attempt coverage and durable failure accounting remain CFO-2a2b. Billing/pricing remains CFO-2a3.

## 9. Pinned primary evidence

- [Google Gemini GenerateContentResponse](https://ai.google.dev/api/generate-content?hl=ja#UsageMetadata) —
  `usageMetadata` is output-only token-usage metadata; `responseId` identifies each response; prompt, candidates,
  cached, tool, thoughts, and total token fields are separately defined.
- [OpenTelemetry GenAI spans at commit 46d43c8](https://github.com/open-telemetry/semantic-conventions-genai/blob/46d43c8949afb53765a202e89f4534eeb75ca3fa/docs/gen-ai/gen-ai-spans.md) —
  operation/provider are required; response ID/model and provider usage attributes are recommended; content
  attributes are opt-in and sensitive.
- [OpenTelemetry Google GenAI reference scenario at commit 46d43c8](https://github.com/open-telemetry/semantic-conventions-genai/blob/46d43c8949afb53765a202e89f4534eeb75ca3fa/reference/scenarios/google-genai/scenario.py) —
  provider usage metadata maps to `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`.

## 10. CFO-2a2.1 completion evidence

- Luna implementation commits: `97a04baef1dd4bbc647d64835e41ca8c8deda4c6` and review fix
  `105922f65ba372ee967ef8748019d14e4681dbbe`.
- Initial RED: existing 10 tests passed and the two new tests failed only because the export did not exist.
- Review-fix RED: 11/12 passed; the sole failure was the missing conditionally required `server.port: 443`.
- Fresh Sol verification on the final head: focused 12/12, CFO 254/254, full suite 892/892, zero failures; syntax and
  diff checks passed.
- Ponytail gate: exactly two existing files; 43 production additions and 50 test additions, 93 total.
- Fresh final re-review: Critical 0, Important 0, ship.
- No I/O, dependency, OpenTelemetry SDK, collector, exporter, database, pricing, Gemini call-site, or Live behavior
  was added. Those remain explicit later slices, so CFO-2a2 itself remains active.

## 11. CFO-2a2.2 — append-only usage storage

CFO-2a2.2 is split so a database, RPC client, and provider call-site are never introduced in one batch:

```mermaid
flowchart LR
    A[2a2.2a\nTable + privacy boundary] --> B[2a2.2b\nIdempotent append RPC]
    B --> C[2a2.2c\nNode RPC client]
    C --> D[2a2.3\nReal Gemini call wiring]

    A -. disposable local PostgreSQL .-> V[Schema E2E]
    D --> DONE[Stored evidence + correlated span]
```

### CFO-2a2.2a — verified

Add `public.lm_cfo_model_usage_evidence` as a structured table. Do not store a raw response or duplicated
`otel_attributes` JSON. Required columns are:

- opaque `public_ref`, owner `uid`, canonical-registry `financial_unit_id` matching `^[a-z][a-z0-9_]*$`, and
  `attribution_status`;
- `provider`, `provider_request_id`, `usage_sequence`, `occurred_at`, and 32-hex `trace_id`;
- requested/response model;
- required input/output/total token counts and nullable cached/reasoning/tool counts;
- `evidence_status` and `created_at`.

The dedupe identity is `(provider, provider_request_id, usage_sequence)`. All counts are non-negative `bigint`;
optional absence is SQL `NULL`, not zero. Provider totals are stored as given and are not constrained to equal a
locally recomputed component sum. Attribution is closed: `attributed` requires a non-null financial unit;
`unattributed` requires null.

The table is append-only. `service_role` receives only SELECT/INSERT; anon/authenticated/public receive nothing;
RLS has service-role SELECT/INSERT policies; an UPDATE/DELETE trigger rejects mutation even by a privileged writer.
CFO-2a2.2a creates no RPC, client, scheduler, exporter, or call-site and is not applied to production. It is verified
against a disposable local PostgreSQL instance. The later append RPC owns identical-retry and conflicting-retry
behavior; the schema's unique constraint owns concurrent dedupe.

Soft target: one migration, one dedicated static test, and one `test:cfo` script entry; at most three files and
100 added LOC total. If the privacy/append-only boundary cannot fit, reduce formatting before adding abstraction.

### CFO-2a2.2a acceptance

- [x] The table has one non-null composite unique dedupe key and never stores raw content or generic metadata JSON.
- [x] Required counts reject null/negative values; optional counts preserve null and explicit zero.
- [x] Attribution state and financial-unit nullability cannot contradict each other.
- [x] Financial-unit IDs use the canonical registry grammar and reject a leading digit.
- [x] RLS, grants, and the trigger permit service SELECT/INSERT only and reject UPDATE/DELETE.
- [x] A disposable local PostgreSQL E2E proves valid insert, duplicate rejection, invalid-count rejection, and
      append-only rejection without touching production.
- [x] The focused migration test, CFO suite, and full suite pass.

### CFO-2a2.2a completion evidence

- Luna implementation commits: `33882cfd7`, `884f76638`, `0709344a5`, and canonical registry fix `f30a5d365`.
- RED gates independently failed for the absent migration, incomplete ACL reset, forbidden content/metadata columns,
  and the non-canonical financial-unit grammar before each minimal fix.
- Fresh Sol verification on the final head: focused 1/1 and full suite 893/893, with zero failures.
- Fresh disposable PostgreSQL 18 E2E started from intentionally broad default ACLs, then proved exact service-role
  SELECT/INSERT and sequence usage, RLS, two real inserts, nullable/zero preservation, dedupe, invalid-count and
  attribution rejection, canonical financial-unit rejection, and append-only behavior.
- Ponytail gate: exactly three implementation files and 67 additions, with no RPC, client, scheduler, provider
  call-site, SDK, exporter, pricing, content, generic metadata, or production apply.
- Fresh final review: Critical 0, Important 0, ship.

### CFO-2a2.2b — verified

Add one `SECURITY INVOKER` function, `public.lm_append_cfo_model_usage_evidence`, in a new forward migration. The
function accepts the table's 17 evidence fields as typed scalar arguments and `RETURNS jsonb`; it accepts or stores
no JSON/JSONB evidence input, content, metadata, price, span, or billing value. The JSON return is only the closed
six-key receipt. The function inserts with the named composite unique constraint as the conflict arbiter.

```mermaid
flowchart TD
    A[Typed evidence call] --> B[INSERT ON CONFLICT DO NOTHING]
    B -->|new identity| C[Return closed receipt]
    B -->|existing identity| D[Read stored row]
    D -->|all 17 fields identical| C
    D -->|any field differs| E[Fixed identity-conflict error]
```

The closed receipt has exactly `public_ref`, `provider`, `provider_request_id`, `usage_sequence`, `trace_id`, and
`created_at`. It never returns owner, financial unit, token counts, models, or content. An identical retry returns
the original receipt without another row. A retry with the same `(provider, provider_request_id, usage_sequence)`
and any different stored field that independently satisfies the existing schema raises
`provider_usage_identity_conflict` with SQLSTATE `23505`; invalid values still fail at the schema boundary. It never
updates. Concurrent calls use the existing unique constraint and the insert-then-read path, not an application lock.

The function runs with caller privileges and fixed `search_path = public, pg_temp`. Function execute privileges
are reset for PUBLIC, anon, authenticated, and service_role before granting only service_role. Table grants remain
unchanged. This slice creates no client, call-site, write-attempt ledger, SDK, exporter, scheduler, or production
apply.

Soft target: one forward migration plus the existing migration test, two files and 95 additions. The local
PostgreSQL E2E must prove first insert, identical retry, conflicting retry, simultaneous duplicate dedupe, fixed
receipt keys, and anon/authenticated denial.

### CFO-2a2.2b acceptance

- [x] One typed RPC inserts a valid row and returns the exact closed six-key receipt.
- [x] An identical sequential or concurrent retry returns the same `public_ref` and leaves exactly one row.
- [x] A changed ownership, token, optional-null, or trace fact under the same identity returns only the fixed
      conflict and never mutates the stored row.
- [x] The function is invoker-security with fixed search path; only service_role can execute it.
- [x] A disposable local PostgreSQL E2E and the focused/CFO/full suites pass without production apply.

### CFO-2a2.2b completion evidence

- Luna implementation commit: `6d1a86ecc`; RED was schema test 1/1 plus RPC test 0/1 only for the absent migration.
- Fresh Sol verification: focused 2/2 and full aggregate 894/894 with zero failures; diff check passed.
- Fresh disposable PostgreSQL 18 E2E proved exact first/retry receipt, four schema-valid fixed conflicts, receipt and
  error privacy, anon/authenticated denial, service mutation denial, and named Session B lock-waiting behind
  uncommitted Session A before both returned one shared receipt and one row.
- Ponytail gate: exactly two files and 57 additions; no JSON evidence input, client, provider call-site, SDK,
  exporter, scheduler, pricing, billing, write-attempt ledger, production apply, or remote DB mutation.
- Task review and fresh final whole-plan review: Critical 0, Important 0, ship.

### CFO-2a2.2c — verified

Add one thin Node client, `appendGeminiUsageEvidence(response, context, options)`. It reuses the verified
`normalizeGeminiUsageEvidence` contract and shared `createCfoSupabaseRpc` transport; it adds no provider call,
tokenizer, retry loop, SDK, exporter, scheduler, or new validation framework.

```mermaid
flowchart LR
    A[Gemini response + context] --> B[Verified normalizer]
    B --> C[17 scalar RPC arguments]
    C --> D[Existing PostgREST helper]
    D --> E[Exact six-key frozen receipt]
```

The client maps `owner_id` to `p_uid`, the fixed non-null financial unit to `attributed`, and every provider count
without recomputing totals. Missing optional counts remain `null`; explicit zero remains zero. `schema_version` and
`otel_attributes` are not sent. The client makes exactly one POST to
`/rest/v1/rpc/lm_append_cfo_model_usage_evidence`, then accepts only the six-key receipt whose provider identity,
sequence, and trace ID exactly echo the normalized evidence. It clones and freezes the receipt.

All local failures use `cfo_provider_usage_store_failed:<fixed_reason>` and never contain response/context values,
provider bodies, credentials, content, IDs, model names, or token counts. A non-2xx response body is not read and
there is no client retry; the database RPC owns idempotency.

Soft target: one client, one focused test, and one `test:cfo` entry; three files and 100 additions. CFO-2a2.2c
does not call Gemini, emit a span, apply migrations, or touch production/remote services.

### CFO-2a2.2c acceptance

- [x] One literal Gemini response/context creates one exact 17-key scalar RPC body and one request.
- [x] Missing optional counts remain null, explicit zero remains zero, and provider total is not recomputed.
- [x] Content-shaped response fields and OpenTelemetry attributes never enter the request, receipt, or error.
- [x] Receipt identity is exact, cloned, deeply frozen, and limited to six keys.
- [x] Invalid input, hostile network/response, invalid receipt, and non-2xx paths are fixed, silent, and single-call.
- [x] Focused, CFO, and full suites pass without a real provider call or production mutation.

### CFO-2a2.2c completion evidence

- Luna implementation commit: `e73427079`; RED stopped only at the planned missing module before test registration.
- Fresh Sol verification: focused 3/3 and full aggregate 897/897 with zero failures; diff and syntax checks passed.
- One literal request proved exact headers and 17 scalar arguments, provider total `99` distinct from input+output,
  optional null/zero preservation, and exclusion of content, schema, and OTel fields.
- Receipt and failure tests proved exact cloned/frozen six-key output, identity mismatch, hostile extra-key response,
  network failure, non-2xx body non-read, one call, fixed errors, and zero console output.
- Ponytail gate: exactly three files and 57 additions; no provider call, database apply, SDK/exporter, scheduler,
  retry loop, pricing, billing, or production/remote request.
- Task review and fresh final whole-plan review: Critical 0, Important 0, ship.

### PostgreSQL evidence

- [Unique constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS)
  — a multi-column unique constraint enforces uniqueness across the listed combination and creates a unique index.
- [Row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — after RLS is enabled,
  normal access requires an applicable policy; command- and role-specific policies separate SELECT from INSERT.
- [INSERT / ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html) — later CFO-2a2.2b uses the unique
  key as its conflict arbiter; CFO-2a2.2a defines the invariant but adds no retry RPC.
- [CREATE FUNCTION](https://www.postgresql.org/docs/current/sql-createfunction.html) — invoker security uses the
  caller's privileges; PostgreSQL also documents fixed search paths and revoking default PUBLIC execute access.
- [PostgREST functions as RPC](https://docs.postgrest.org/en/stable/references/api/functions.html#calling-with-post)
  — a JSON object's keys become named PostgreSQL function arguments under the `/rpc` route.
