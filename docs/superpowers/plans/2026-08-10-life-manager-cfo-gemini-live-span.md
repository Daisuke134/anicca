# CFO-2a2.4c3 Gemini Live Span Implementation Plan

**Status:** READY — fresh Sol review returned `ship`; ready for Luna implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Correlate one successfully stored Gemini Live usage observation with one truthful, content-free OTel span.

**Architecture:** Extend the existing provider usage span module and tests. Reuse its tracer lifecycle/error contract,
the 4b Live normalizer, and the 4c2 Live store. Start a span, derive trace/time, normalize, store once, then finish the
span. Add no module, dependency, migration, service, or bridge wiring.

**Tech Stack:** CommonJS, OpenTelemetry API/Node SDK already pinned, Node built-in `node:test`.

## Global constraints

- Luna owns exactly `apps/life-call/lib/cfo-provider-usage-span.js` and
  `apps/life-call/lib/cfo-provider-usage-span.test.js`; Sol owns docs/review/verification/commit/push.
- Soft targets: at most 35 production additions and 35 test additions; exactly two files / at most 70 additions total.
- Preserve `captureGeminiGenerateContent`, its public behavior, span name, attributes, ordering, errors, and tests.
- No migration/database deployment, real provider call, WebSocket/server/bridge, aggregation, duration estimate,
  scheduler, launchd, Telegram, logging, retry, dependency, or exported abstraction beyond the one Live function.
- Run every command from `apps/life-call`. Do not commit or push.

## Task 1: Capture one stored Live observation

- [ ] **Step 1 — write the smallest RED tests**

Add one success test with an in-memory exporter, injected clock, injected append, and a Live content sentinel. Require:

- exact CLIENT span name `generate_content models/gemini-2.5-flash-native-audio-preview-09-2025`;
- append called once with the original message, context extended only by the injected RFC3339 `occurred_at` and the
  nonzero 32-hex recording trace ID, and unchanged store options;
- append observes zero finished spans, proving success ends only after storage;
- the append callback builds its receipt from `context.trace_id`; returned receipt, append context, and finished span
  therefore have the same generated trace ID;
- one finished span has the normalized Live OTel attributes/counts, no events, and no sentinel/content/raw metadata.

Add one compact failure test covering invalid message, append failure, and one Live-specific zero-trace recording
case. A caller context other than the exact five-key shape below fails `invalid_input` before span/append. Invalid
message ends one fixed `invalid_response` error span and makes zero append calls. Append failure ends one `store`
error span. The zero-trace case makes zero append calls, throws fixed `tracing`, and leaves one ended CLIENT span.
Every error span is exact Live base attributes plus its one `error.type`: it has no `gen_ai.usage.*`, response
attribute, event, content, log, or retry. Existing tests cover the rest of the unavailable/non-recording matrix.

Freeze these exact test shapes:

```js
const LIVE_CONTEXT = {
  owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: LIVE_MODEL,
  live_session_id: "2".repeat(32), usage_sequence: 7,
};
const LIVE_RECEIPT = {
  public_ref: "30000000-0000-4000-8000-000000000003", provider: "gcp.gemini",
  local_correlation_id: `live-session:${LIVE_CONTEXT.live_session_id}`, usage_sequence: 7,
  trace_id: "1".repeat(32), created_at: TIME,
};
const LIVE_BASE = {
  "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini",
  "gen_ai.request.model": LIVE_MODEL, "gen_ai.request.stream": true, "gen_ai.output.type": "speech",
  "server.address": "generativelanguage.googleapis.com", "server.port": 443,
};
```

Use one self-contained compact failure test for the pre-span matrix and all three post-span failures:

```js
test("fails Live observation with fixed reasons and closed spans", async t => {
  const { exporter, tracer } = owned(t);
  const zeroExporter = new InMemorySpanExporter();
  const zeroProvider = new NodeTracerProvider({
    idGenerator: { generateTraceId: () => "0".repeat(32), generateSpanId: () => "0".repeat(16) },
    spanProcessors: [new SimpleSpanProcessor(zeroExporter)],
  });
  t.after(() => zeroProvider.shutdown());
  let logs = 0, appends = 0;
  const original = [console.log, console.error, console.warn];
  const validOptions = { tracer, now: () => TIME, append: async () => { appends += 1; } };
  const storeFailOptions = { tracer, now: () => TIME, append: async () => {
    appends += 1; throw new Error("LIVE_OUTPUT_SENTINEL");
  } };
  const zeroTraceOptions = { tracer: zeroProvider.getTracer("cfo-live-zero"), now: () => TIME,
    append: async () => { appends += 1; } };
  console.log = console.error = console.warn = () => { logs += 1; };
  try {
    for (const context of [
      { ...LIVE_CONTEXT, live_session_id: "0".repeat(32) },
      { ...LIVE_CONTEXT, usage_sequence: -1 },
      { ...LIVE_CONTEXT, occurred_at: TIME },
      { ...LIVE_CONTEXT, trace_id: "1".repeat(32) },
    ]) await rejects(() => captureGeminiLiveUsageObservation(LIVE_MESSAGE, context, validOptions), /^cfo_provider_usage_span_failed:invalid_input$/);
    assert.equal(exporter.getFinishedSpans().length, 0);
    assert.equal(appends, 0);
    await rejects(() => captureGeminiLiveUsageObservation({}, LIVE_CONTEXT, validOptions), /^cfo_provider_usage_span_failed:invalid_response$/);
    await rejects(() => captureGeminiLiveUsageObservation(LIVE_MESSAGE, LIVE_CONTEXT, storeFailOptions), /^cfo_provider_usage_span_failed:store$/);
    await rejects(() => captureGeminiLiveUsageObservation(LIVE_MESSAGE, LIVE_CONTEXT, zeroTraceOptions), /^cfo_provider_usage_span_failed:tracing$/);
  } finally {
    [console.log, console.error, console.warn] = original;
  }
  assert.equal(exporter.getFinishedSpans().length, 2);
  assert.equal(zeroExporter.getFinishedSpans().length, 1);
  const [invalid, stored] = exporter.getFinishedSpans(), [zero] = zeroExporter.getFinishedSpans();
  for (const [span, reason] of [[invalid, "invalid_response"], [stored, "store"], [zero, "tracing"]]) {
    assert.equal(span.kind, SpanKind.CLIENT);
    assert.equal(span.name, `generate_content ${LIVE_MODEL}`);
    assert.equal(span.ended, true);
    assert.equal(span.status.code, SpanStatusCode.ERROR);
    assert.deepEqual(span.attributes, { ...LIVE_BASE, "error.type": reason });
    assert.equal(span.events.length, 0);
    assert.equal(Object.keys(span.attributes).some((key) => key.startsWith("gen_ai.usage.")), false);
  }
  assert.equal(appends, 1);
  assert.equal(logs, 0);
});
```

The success append builds the receipt from the actual context and proves the three-way join:

```js
const { exporter, tracer } = owned(t);
let seen;
const value = await captureGeminiLiveUsageObservation(LIVE_MESSAGE, LIVE_CONTEXT, {
  tracer, now: () => TIME, storeOptions: { marker: "store" },
  append: async (message, context, options) => {
  seen = { message, context, options, finished: exporter.getFinishedSpans().length };
  return { ...LIVE_RECEIPT, trace_id: context.trace_id };
  },
});
const [span] = exporter.getFinishedSpans();
assert.equal(value.trace_id, seen.context.trace_id);
assert.equal(value.trace_id, span.spanContext().traceId);
```

- [ ] **Step 2 — run RED**

```bash
node --test lib/cfo-provider-usage-span.test.js
```

Expected: the four historical GenerateContent tests pass and only the two new Live tests fail because the export is
absent.

- [ ] **Step 3 — add the minimum span extension**

Import the Live normalizer/store and define the exact Live model/name constants. Reuse or minimally generalize the
existing option validator so the default append is path-specific. The Live function accepts an already-received
message and the exact five-key caller context above. Validate own enumerable string keys, owner, fixed unit/model,
nonzero 32-hex `live_session_id`, and non-negative safe-integer `usage_sequence` before starting a span. It then starts
one recording CLIENT span with this exact base:

```js
const LIVE_CONTEXT_KEYS = ["owner_id", "financial_unit_id", "request_model", "live_session_id", "usage_sequence"];
const keys = Object.keys(context);
const closed = keys.length === LIVE_CONTEXT_KEYS.length && LIVE_CONTEXT_KEYS.every((key) => keys.includes(key));
```

```js
const LIVE_BASE_ATTRIBUTES = {
  "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini",
  "gen_ai.request.model": LIVE_REQUEST_MODEL, "gen_ai.request.stream": true,
  "gen_ai.output.type": "speech", "server.address": "generativelanguage.googleapis.com", "server.port": 443,
};
```

Create a context with the
clock time and span trace, normalizes, appends once, then sets normalized attributes and ends success. On normalize or
store failure, finish the same span once with only a fixed `error.type`, throw the existing fixed-prefix error, and do
not retry or log. Return the closed append receipt.

Keep the ordered control flow exact; do not edit `captureGeminiGenerateContent`:

```js
validate exact context/options -> start recording span -> validate trace -> inject time/trace
-> normalize -> append once -> set normalized attributes -> end once -> return receipt
```

- [ ] **Step 4 — run GREEN and scope gates**

```bash
node --test lib/cfo-provider-usage-span.test.js
npm run test:cfo
npm test
node --check lib/cfo-provider-usage-span.js
git diff --check -- lib/cfo-provider-usage-span.js lib/cfo-provider-usage-span.test.js
git diff --numstat -- lib/cfo-provider-usage-span.js lib/cfo-provider-usage-span.test.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 2 && added <= 70) }'
```

Expected: all commands exit `0`; exactly two files and at most 70 additions. Return exact RED/GREEN totals and line
counts to Sol. Do not commit or push.

## Plan self-review

- Truth: provider counts are span attributes; observation sequence is preserved, never summed.
- Correlation: the stored row receives the exact recording span trace ID and injected observation time.
- Ordering: success exists only after append succeeds; failures close the same span once.
- Privacy: span name/attributes/errors contain no message content or raw metadata.
- YAGNI: two existing files, one new export, no bridge or deployment.
- Placeholders: none. Function, model/name, ordering, errors, tests, commands, and size limit are fixed.
