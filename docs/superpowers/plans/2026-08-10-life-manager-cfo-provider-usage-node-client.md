# Life Manager CFO-2a2.2c Provider Usage Node Client Plan

**Status:** READY — one Luna task; client boundary only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan.
> Luna owns production code/tests/implementation commands. Sol owns plan, final verification, closure, and push.

**Goal:** Send one verified Gemini usage fact to the idempotent database RPC and return one closed receipt.

**Architecture:** Reuse `normalizeGeminiUsageEvidence` for all provider semantics and `createCfoSupabaseRpc` for
credentials, one POST, fixed transport errors, and JSON parsing. Add only the mapping and receipt boundary.

**Tech stack:** Node.js CommonJS, built-in `node:test`, existing global/fake fetch; no dependency.

## Global constraints — Ponytail gate

- Create `lib/cfo-provider-usage-store.js` and its test; modify only the `test:cfo` script entry.
- Soft target: 40 production + 55 test + one script addition; three files and 100 additions total.
- No new generic validator, HTTP helper, retry, logger, class, state, migration, database test, Gemini call,
  OpenTelemetry SDK/exporter, price/billing, launchd, or production/remote request.
- Reuse tested hostile-shape behavior instead of duplicating its full matrix. Add only one normal path and the
  minimum regressions for wrong token values, leaked content, duplicate requests, and invalid receipts.

## Task 1 — Add the thin Gemini usage storage client

**Files**

- Create: `apps/life-call/lib/cfo-provider-usage-store.js`
- Create: `apps/life-call/lib/cfo-provider-usage-store.test.js`
- Modify: `apps/life-call/package.json`

- [ ] **Step 1 — Write three focused tests and run RED**

Test 1 supplies one literal Gemini response/context with content-shaped extra fields, one absent optional count, and
one explicit optional zero. Assert exactly one request to
`/rest/v1/rpc/lm_append_cfo_model_usage_evidence`, exact service-role headers, and the exact 17 named scalar
arguments. Assert total remains the provider total and request JSON contains no schema, OTel, content, prompt,
candidate, tool argument, credential, or raw-response field. Validate the returned receipt is an isolated frozen
six-key object.

Test 2 proves invalid response/context fails before fetch with only `cfo_provider_usage_store_failed:invalid_input`.

Test 3 includes both (a) a validly typed receipt with a different `provider_request_id` and (b) an extra-key or
accessor receipt. It also proves one thrown network value and one non-2xx response each make at most one request,
never read a non-2xx body, never log, and expose only fixed redacted errors. Reuse the shared helper's existing
matrix; do not duplicate every hostile object shape here.

Use this executable three-test structure; keep the same cases and reduce repetition only with local fixture helpers:

```js
"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { appendGeminiUsageEvidence } = require("./cfo-provider-usage-store.js");

const URL = "https://project.supabase.co", KEY = "service-role-fixture";
const RESPONSE = { responseId: "provider-response-id", modelVersion: "gemini-2.5-flash-001",
  usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 4, totalTokenCount: 99, thoughtsTokenCount: 0 },
  candidates: [{ text: "CONTENT_SENTINEL" }], unknown: "RAW_SENTINEL" };
const CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas",
  occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "11111111111111111111111111111111",
  request_model: "gemini-2.5-flash" };
const RECEIPT = { public_ref: "30000000-0000-4000-8000-000000000001", provider: "gcp.gemini",
  provider_request_id: "provider-response-id", usage_sequence: 0,
  trace_id: CONTEXT.trace_id, created_at: "2026-08-10T01:02:04.000Z" };
const http = (body = RECEIPT, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });

test("maps one normalized Gemini usage fact to one exact RPC", async () => {
  const calls = [], providerReceipt = { ...RECEIPT };
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return http(providerReceipt); };
  const value = await appendGeminiUsageEvidence(RESPONSE, CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_model_usage_evidence`);
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_uid: "u1", p_financial_unit_id: "life_manager_saas", p_attribution_status: "attributed",
    p_provider: "gcp.gemini", p_provider_request_id: "provider-response-id", p_usage_sequence: 0,
    p_occurred_at: CONTEXT.occurred_at, p_trace_id: CONTEXT.trace_id,
    p_request_model: CONTEXT.request_model, p_response_model: "gemini-2.5-flash-001",
    p_input_tokens: 10, p_output_tokens: 4, p_total_tokens: 99,
    p_cached_input_tokens: null, p_reasoning_output_tokens: 0, p_tool_input_tokens: null,
    p_evidence_status: "provider_reported",
  });
  assert.doesNotMatch(calls[0].init.body, /CONTENT_SENTINEL|RAW_SENTINEL|otel_attributes|schema_version/);
  assert.deepEqual(value, RECEIPT); assert.equal(Object.isFrozen(value), true);
  providerReceipt.trace_id = "22222222222222222222222222222222"; assert.deepEqual(value, RECEIPT);
});

test("rejects invalid provider input before fetch", async () => {
  let calls = 0; const invalid = { ...RESPONSE }; delete invalid.responseId;
  await assert.rejects(
    () => appendGeminiUsageEvidence(invalid, CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; } }),
    /^cfo_provider_usage_store_failed:invalid_input$/,
  );
  assert.equal(calls, 0);
});

test("fails closed on receipt and transport boundaries without retry or logs", async () => {
  const original = [console.log, console.error, console.warn]; let logs = 0, calls = 0, jsonCalls = 0;
  console.log = console.error = console.warn = () => { logs += 1; };
  const run = (fetchImpl, pattern) => assert.rejects(
    () => appendGeminiUsageEvidence(RESPONSE, CONTEXT, { supaUrl: URL, supaKey: KEY,
      fetchImpl: async (...args) => { calls += 1; return fetchImpl(...args); } }), pattern,
  );
  try {
    await run(async () => http({ ...RECEIPT, provider_request_id: "other-response" }),
      /^cfo_provider_usage_store_failed:receipt_mismatch$/);
    await run(async () => http({ ...RECEIPT, extra: "RAW_SENTINEL" }),
      /^cfo_provider_usage_store_failed:invalid_receipt$/);
    await run(async () => { throw new Error("CONTENT_SENTINEL"); },
      /^cfo_provider_usage_store_failed:network$/);
    await run(async () => ({ ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("RAW_SENTINEL"); } }),
      /^cfo_provider_usage_store_failed:provider_409$/);
  } finally { [console.log, console.error, console.warn] = original; }
  assert.equal(calls, 4); assert.equal(jsonCalls, 0); assert.equal(logs, 0);
});
```

Add this test once to `test:cfo`. Run:

```bash
node --test lib/cfo-provider-usage-store.test.js
```

Expected RED: all three fail only because the new module does not exist.

- [ ] **Step 2 — Implement the minimal client**

Export only `appendGeminiUsageEvidence(response, context, options = {})`.

1. Normalize with `normalizeGeminiUsageEvidence`; map any normalizer failure to fixed `invalid_input`.
2. Validate options through the shared helper.
3. POST once through `postRpc` with exactly these keys:

```text
p_uid, p_financial_unit_id, p_attribution_status,
p_provider, p_provider_request_id, p_usage_sequence, p_occurred_at, p_trace_id,
p_request_model, p_response_model,
p_input_tokens, p_output_tokens, p_total_tokens,
p_cached_input_tokens, p_reasoning_output_tokens, p_tool_input_tokens,
p_evidence_status
```

`p_attribution_status` is `attributed` because the verified Gemini context requires the fixed non-null Life Manager
financial unit. Map optional token `null`/zero literally. Do not send `schema_version` or `otel_attributes`.

4. Accept exactly `public_ref`, `provider`, `provider_request_id`, `usage_sequence`, `trace_id`, `created_at`.
Validate non-zero UUID/timestamp and exact identity echo, then clone and deep-freeze. Map validation failures to
fixed `invalid_receipt` or `receipt_mismatch` without reading unknown values into an error.

The implementation follows this literal mapping/validation skeleton; keep it compact and use the shared helpers:

```js
const ERROR_PREFIX = "cfo_provider_usage_store_failed:";
const RECEIPT_KEYS = new Set(["public_ref", "provider", "provider_request_id", "usage_sequence", "trace_id", "created_at"]);
const { fail, internal, exact, uuid, timestamp, validateOptions, freeze, postRpc } = createCfoSupabaseRpc(ERROR_PREFIX);

function receipt(value, expected) {
  exact(value, RECEIPT_KEYS, "invalid_receipt");
  const public_ref = uuid(value.public_ref, "invalid_receipt");
  if (!timestamp(value.created_at)) fail("invalid_receipt");
  if (value.provider !== expected.provider || value.provider_request_id !== expected.provider_request_id
      || value.usage_sequence !== expected.usage_sequence || value.trace_id !== expected.trace_id) fail("receipt_mismatch");
  try { return freeze(structuredClone({ public_ref, provider: value.provider, provider_request_id: value.provider_request_id,
    usage_sequence: value.usage_sequence, trace_id: value.trace_id, created_at: value.created_at })); }
  catch { fail("invalid_receipt"); }
}

async function appendGeminiUsageEvidence(response, context, options = {}) {
  let evidence, config;
  try { evidence = normalizeGeminiUsageEvidence(response, context); config = validateOptions(options); }
  catch (error) { if (internal(error)) throw error; fail("invalid_input"); }
  const t = evidence.tokens;
  const body = { p_uid: evidence.owner_id, p_financial_unit_id: evidence.financial_unit_id,
    p_attribution_status: "attributed", p_provider: evidence.provider,
    p_provider_request_id: evidence.provider_request_id, p_usage_sequence: evidence.usage_sequence,
    p_occurred_at: evidence.occurred_at, p_trace_id: evidence.trace_id,
    p_request_model: evidence.request_model, p_response_model: evidence.response_model,
    p_input_tokens: t.input, p_output_tokens: t.output, p_total_tokens: t.total,
    p_cached_input_tokens: t.cached_input, p_reasoning_output_tokens: t.reasoning_output,
    p_tool_input_tokens: t.tool_input, p_evidence_status: evidence.evidence_status };
  return receipt(await postRpc(config, "lm_append_cfo_model_usage_evidence", body), evidence);
}
```

- [ ] **Step 3 — Run focused and repository GREEN**

```bash
node --test lib/cfo-provider-usage-store.test.js
npm run test:cfo
npm test
git diff --check
```

Expected: focused 3/3; CFO 259/259; full aggregate 897/897; failures zero.

- [ ] **Step 4 — Enforce scope and commit**

Verify exact three files and at most 100 additions. Commit only them as
`feat(cfo): add provider usage rpc client`; do not push. Record RED/GREEN/request/receipt/privacy/LOC evidence in
the ignored SDD report. Sol performs fresh review, independent focused/full verification, spec closure, fetch, and
push.
