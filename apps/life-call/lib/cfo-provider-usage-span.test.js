"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { SpanKind, SpanStatusCode, trace } = require("@opentelemetry/api");
const { NodeTracerProvider, SimpleSpanProcessor, InMemorySpanExporter } = require("@opentelemetry/sdk-trace-node");
const { captureGeminiGenerateContent } = require("./cfo-provider-usage-span.js");
const CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: "gemini-2.5-flash" }, TIME = "2026-08-10T01:02:03.000Z";
const RESPONSE = { responseId: "provider-response-id", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 4, totalTokenCount: 99, cachedContentTokenCount: 2, thoughtsTokenCount: 3, toolUsePromptTokenCount: 1 }, prompt: "CONTENT_SENTINEL", candidates: [{ content: { parts: [{ text: "CONTENT_SENTINEL" }] } }] };
const ATTRS = { "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": "gemini-2.5-flash", "gen_ai.response.id": "provider-response-id", "gen_ai.response.model": "gemini-2.5-flash-001", "gen_ai.usage.input_tokens": 10, "gen_ai.usage.output_tokens": 7, "gen_ai.usage.cache_read.input_tokens": 2, "gen_ai.usage.reasoning.output_tokens": 3, "server.address": "generativelanguage.googleapis.com", "server.port": 443 };
const rejects = (call, pattern) => assert.rejects(call, error => { assert.match(error.message, pattern); return true; });
function owned(t) { const exporter = new InMemorySpanExporter(); const provider = new NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] }); t.after(() => provider.shutdown()); return { exporter, tracer: provider.getTracer("cfo-test") }; }

test("records one content-free CLIENT span and appends its trace", async t => {
  const { exporter, tracer } = owned(t); let seen;
  const value = await captureGeminiGenerateContent(async () => RESPONSE, CONTEXT, { tracer, now: () => TIME, storeOptions: { marker: "store" }, append: async (response, context, options) => { seen = { response, context, options, finished: exporter.getFinishedSpans().length }; return { ok: true }; } });
  const [span] = exporter.getFinishedSpans(); assert.strictEqual(value, RESPONSE); assert.equal(seen.response, RESPONSE); assert.equal(seen.finished, 1); assert.deepEqual(seen.options, { marker: "store" }); assert.deepEqual(span.attributes, ATTRS); assert.equal(span.kind, SpanKind.CLIENT); assert.equal(span.name, "generate_content gemini-2.5-flash"); assert.equal(span.ended, true); assert.match(span.spanContext().traceId, /^(?!0{32})[0-9a-f]{32}$/); assert.equal(seen.context.trace_id, span.spanContext().traceId); assert.deepEqual(seen.context, { ...CONTEXT, occurred_at: TIME, trace_id: span.spanContext().traceId }); assert.equal(span.events.length, 0); assert.doesNotMatch(JSON.stringify({ attributes: span.attributes, status: span.status, events: span.events, context: seen.context }), /CONTENT_SENTINEL/);
});

test("fails with fixed reasons and closed error spans", async t => {
  const { exporter, tracer } = owned(t); const noop = trace.getTracer("cfo-noop"); let requests = 0, appends = 0;
  const opts = { tracer, now: () => TIME, append: async () => { appends += 1; } };
  await rejects(() => captureGeminiGenerateContent(async () => { requests += 1; }, { ...CONTEXT, owner_id: "" }, opts), /^cfo_provider_usage_span_failed:invalid_input$/);
  await rejects(() => captureGeminiGenerateContent(async () => { requests += 1; }, CONTEXT, { ...opts, tracer: noop }), /^cfo_provider_usage_span_failed:tracing$/);
  await rejects(() => captureGeminiGenerateContent(async () => { requests += 1; throw new Error("CONTENT_SENTINEL"); }, CONTEXT, opts), /^cfo_provider_usage_span_failed:provider$/);
  await rejects(() => captureGeminiGenerateContent(async () => { requests += 1; return { ...RESPONSE, usageMetadata: { ...RESPONSE.usageMetadata, totalTokenCount: -1 } }; }, CONTEXT, opts), /^cfo_provider_usage_span_failed:invalid_response$/);
  assert.equal(requests, 2); assert.equal(appends, 0); const spans = exporter.getFinishedSpans(); assert.equal(spans.length, 2);
  for (const [span, reason] of spans.map((span, index) => [span, index ? "invalid_response" : "provider"])) { assert.equal(span.kind, SpanKind.CLIENT); assert.equal(span.name, "generate_content gemini-2.5-flash"); assert.equal(span.ended, true); assert.equal(span.status.code, SpanStatusCode.ERROR); assert.equal(span.attributes["error.type"], reason); assert.equal(span.attributes["gen_ai.operation.name"], "generate_content"); assert.equal(span.attributes["gen_ai.provider.name"], "gcp.gemini"); assert.equal(span.attributes["gen_ai.request.model"], "gemini-2.5-flash"); assert.equal(span.attributes["server.address"], "generativelanguage.googleapis.com"); assert.equal(span.attributes["server.port"], 443); assert.equal(span.events.length, 0); assert.doesNotMatch(JSON.stringify({ attributes: span.attributes, status: span.status, events: span.events }), /CONTENT_SENTINEL/); }
});

test("ends the model span before a fixed store failure", async t => {
  const { exporter, tracer } = owned(t); let seen;
  await rejects(() => captureGeminiGenerateContent(async () => RESPONSE, CONTEXT, { tracer, now: () => TIME, append: async (_response, context) => { seen = { context, finished: exporter.getFinishedSpans().length }; throw new Error("CONTENT_SENTINEL"); } }), /^cfo_provider_usage_span_failed:store$/);
  const [span] = exporter.getFinishedSpans(); assert.equal(seen.finished, 1); assert.equal(span.ended, true); assert.equal(span.status.code, SpanStatusCode.UNSET); assert.equal(span.attributes["error.type"], undefined); assert.equal(span.events.length, 0); assert.doesNotMatch(JSON.stringify({ attributes: span.attributes, status: span.status, events: span.events, context: seen.context }), /CONTENT_SENTINEL/);
});

test("closes a real recording span when its trace ID is zero", async t => {
  const exporter = new InMemorySpanExporter(), provider = new NodeTracerProvider({ idGenerator: { generateTraceId: () => "00000000000000000000000000000000", generateSpanId: () => "0000000000000000" }, spanProcessors: [new SimpleSpanProcessor(exporter)] }); t.after(() => provider.shutdown()); let requests = 0, appends = 0;
  await rejects(() => captureGeminiGenerateContent(async () => { requests += 1; return RESPONSE; }, CONTEXT, { tracer: provider.getTracer("cfo-zero"), now: () => TIME, append: async () => { appends += 1; } }), /^cfo_provider_usage_span_failed:tracing$/);
  assert.equal(requests, 0); assert.equal(appends, 0); const spans = exporter.getFinishedSpans(); assert.equal(spans.length, 1); const [span] = spans; assert.equal(span.ended, true); assert.equal(span.status.code, SpanStatusCode.ERROR); assert.equal(span.attributes["error.type"], "tracing"); assert.equal(span.name, "generate_content gemini-2.5-flash"); assert.equal(span.attributes["gen_ai.operation.name"], "generate_content"); assert.equal(span.attributes["gen_ai.provider.name"], "gcp.gemini"); assert.equal(span.attributes["gen_ai.request.model"], "gemini-2.5-flash"); assert.equal(span.attributes["server.address"], "generativelanguage.googleapis.com"); assert.equal(span.attributes["server.port"], 443); assert.equal(span.events.length, 0);
});
