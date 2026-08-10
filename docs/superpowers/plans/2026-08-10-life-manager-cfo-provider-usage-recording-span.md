# CFO-2a2.3b Recording Span Helper Plan

**Status:** COMPLETE — real SDK span helper verified; call-site wiring remains separate.

> Luna owns production code/tests/commands. Sol owns this plan, review, final verification, closure, commit, and push.

**Goal:** Wrap one Gemini `generateContent` request in a real content-free CLIENT span, end the span when the model
response is received, then append provider usage with the same trace ID.

**Architecture:** Reuse `normalizeGeminiUsageEvidence` and `appendGeminiUsageEvidence`. One module-scope
`NodeTracerProvider` with `SimpleSpanProcessor(ConsoleSpanExporter)` lives for the service lifetime; never create or
shutdown it per call. Tests inject a real tracer backed by `InMemorySpanExporter`; no fake span is permitted.

## Ponytail gate

- Create `lib/cfo-provider-usage-span.js` and its test; add the test once to `test:cfo`.
- Soft target: 45 production + 54 test + one script addition; three files and 100 additions total.
- No call-site, server startup, global tracer registration, collector, OTLP, queue, retry, price, billing, migration,
  DB apply, Telegram, content attribute, generic provider framework, or unrelated Gemini path.
- Errors expose only `cfo_provider_usage_span_failed:<fixed_reason>` and never provider/request/response values.

## Task 1 — Implement one recording Gemini span boundary

**Files**

- Create: `apps/life-call/lib/cfo-provider-usage-span.js`
- Create: `apps/life-call/lib/cfo-provider-usage-span.test.js`
- Modify: `apps/life-call/package.json`

### Step 1 — Write focused tests and run RED

Export only `captureGeminiGenerateContent(request, context, options = {})`. Tests use a real
`NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(inMemoryExporter)] })` and its tracer.

1. Success: one literal response includes provider metadata plus `CONTENT_SENTINEL` prompt/output-shaped fields.
   Assert strict response identity, one append call, and one ended `SpanKind.CLIENT` named
   `generate_content gemini-2.5-flash`. The append fake must observe that the span is already in the exporter. Assert
   the append context trace ID equals the actual non-zero span trace ID and span attributes equal the existing
   normalizer's closed attributes. Serialized attributes/error/append context must exclude the sentinel.
2. Compact failure table: invalid context and an API no-op tracer fail before request/append with fixed
   `invalid_input` / `tracing`; provider rejection and invalid metadata each yield one ended ERROR span, zero append,
   fixed `provider` / `invalid_response`, fixed matching `error.type`, required base attributes, and no sentinel.
3. Append rejection: the successful model span is already ended with closed attributes, no response is returned,
   and only fixed `store` is exposed.

Register `t.after(() => provider.shutdown())` for every test-owned provider. Add this test once to `test:cfo`, then run:

```bash
node --test lib/cfo-provider-usage-span.test.js
```

Expected RED: missing module only.

### Step 2 — Implement the minimum helper

Constants: request model `gemini-2.5-flash`, span name `generate_content gemini-2.5-flash`, error prefix
`cfo_provider_usage_span_failed:`. Closed reasons are exactly `invalid_input`, `tracing`, `provider`,
`invalid_response`, and `store`; native/injected values never escape. Validate a callable request, non-empty owner,
exact `life_manager_saas`, and exact request model before starting the request.

Default options are the private real tracer, verified append client, `() => new Date().toISOString()`, and append
client defaults. Tests may inject only `tracer`, `append`, `now`, and `storeOptions`.

Execute exactly:

```text
validate closed input
start SpanKind.CLIENT with operation/provider/request-model/server base attributes
require isRecording + non-zero 32-hex trace ID
await request
build { owner_id, financial_unit_id, request_model, occurred_at, trace_id }
normalize response → set exact evidence.otel_attributes
end span
await append(response, same context, storeOptions)
return the original response object
```

Base attributes at span creation are `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`,
`server.address`, and `server.port`. On request/normalization failure add only fixed `error.type: provider` or
`invalid_response`, set ERROR status, and end; never record an exception/description. On append failure the model
span stays successfully ended because DB latency/failure is outside it. End at most once. Clock/normalizer failures
map to `invalid_response`; tracer start/no-op/zero-ID failures map to `tracing`.

### Step 3 — GREEN, scope, and handoff

Run:

```bash
node --test lib/cfo-provider-usage-span.test.js
npm run test:cfo
npm test
node --check lib/cfo-provider-usage-span.js
git diff --check
```

Expected: focused/CFO/full zero failures. Confirm exactly three files, at most 100 additions, no content sentinel in
production code output, and no network call outside injected tests. Do not commit/push. Return RED/GREEN totals,
span kind/name/status/trace correlation, privacy, LOC, and scope evidence to Sol.
