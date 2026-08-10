"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ledgerPath = path.join(__dirname, "ledger.js");

function ledger() {
  assert.ok(fs.existsSync(ledgerPath), "lib/ledger.js must exist");
  delete require.cache[require.resolve(ledgerPath)];
  return require(ledgerPath);
}

test("LM-7 migration creates only the additive lm_api_cost ledger", () => {
  const sqlPath = path.join(__dirname, "../migrations/2026-07-18-lm-api-cost.sql");
  assert.ok(fs.existsSync(sqlPath), "LM-7 migration must exist");
  const sql = fs.readFileSync(sqlPath, "utf8").replace(/\s+/g, " ").trim().toLowerCase();
  assert.match(sql, /create table if not exists lm_api_cost \(id bigint generated always as identity primary key, ts timestamptz default now\(\), uid text, kind text, quantity numeric, unit text, est_usd numeric, meta jsonb\)/);
  assert.doesNotMatch(sql, /\b(drop|truncate|alter)\b/);
});

test("recordCost inserts the normalized row through Supabase REST", async () => {
  const calls = [];
  const fetchImpl = async (...args) => {
    calls.push(args);
    return { ok: true, status: 201 };
  };
  const ok = await ledger().recordCost({
    uid: "u1", kind: "telnyx_call", quantity: 90, unit: "seconds",
    estUsd: 0.003, meta: { event: "wake" },
  }, { supaUrl: "https://db.example", supaKey: "service", fetchImpl });

  assert.equal(ok, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "https://db.example/rest/v1/lm_api_cost");
  assert.equal(calls[0][1].method, "POST");
  assert.equal(calls[0][1].headers.Prefer, "return=minimal");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    uid: "u1", kind: "telnyx_call", quantity: 90, unit: "seconds",
    est_usd: 0.003, meta: { event: "wake" },
  });
});

test("recordCost logs and resolves false when Supabase fails", async () => {
  const errors = [];
  const result = await ledger().recordCost({ uid: "u1", kind: "x", quantity: 1 }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async () => { throw new Error("offline"); },
    log: (...args) => errors.push(args.join(" ")),
  });
  assert.equal(result, false);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /offline/);
});

test("recordDailyComposioPoll uses a DB day query and inserts at most one row", async () => {
  const requests = [];
  const responses = [
    { ok: true, status: 200, json: async () => [] },
    { ok: true, status: 201 },
    { ok: true, status: 200, json: async () => [{ id: 9 }] },
  ];
  const opts = {
    supaUrl: "https://db.example", supaKey: "service",
    nowMs: Date.parse("2026-07-18T12:34:56Z"),
    fetchImpl: async (...args) => { requests.push(args); return responses.shift(); },
  };

  assert.equal(await ledger().recordDailyComposioPoll("u1", opts), true);
  assert.equal(await ledger().recordDailyComposioPoll("u1", opts), false);
  assert.equal(requests.length, 3);
  assert.match(requests[0][0], /kind=eq\.composio_poll/);
  assert.match(requests[0][0], /uid=eq\.u1/);
  assert.match(requests[0][0], /ts=gte\.2026-07-18T00%3A00%3A00\.000Z/);
  assert.match(requests[0][0], /ts=lt\.2026-07-19T00%3A00%3A00\.000Z/);
  assert.equal(requests[1][1].method, "POST");
  assert.equal(requests[2][1].method, undefined);
});

test("monthlyComposioCallCount reads the exact monthly composio_call count", async () => {
  const requests = [];
  const count = await ledger().monthlyComposioCallCount({ nowMs: Date.parse("2026-07-21T12:00:00Z"),
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (...args) => { requests.push(args); return { ok: true, headers: { get: () => "0-0/19500" } }; } });
  assert.equal(count, 19500);
  assert.match(requests[0][0], /kind=eq\.composio_call/);
  assert.match(requests[0][0], /ts=gte\.2026-07-01/);
});

test("businessSummary is pure and groups calls and total cost per uid", () => {
  const rows = [
    { ts: "2026-07-18T10:00:00Z", uid: "u1", kind: "telnyx_call", quantity: "90", est_usd: "0.003" },
    { ts: "2026-07-18T10:00:00Z", uid: "u1", kind: "gemini_live", quantity: 90, est_usd: 0.0345 },
    { ts: "2026-07-17T10:00:00Z", uid: "u2", kind: "telnyx_call", quantity: 30, est_usd: 0.001 },
    { ts: "2026-06-01T10:00:00Z", uid: "old", kind: "telnyx_call", quantity: 600, est_usd: 9 },
  ];
  const frozen = JSON.parse(JSON.stringify(rows));
  const summary = ledger().businessSummary(30, rows, Date.parse("2026-07-18T12:00:00Z"));

  assert.deepEqual(summary, {
    calls: 2,
    call_minutes: 2,
    est_cost_usd: 0.0385,
    per_uid: {
      u1: { calls: 1, call_minutes: 1.5, est_cost_usd: 0.0375 },
      u2: { calls: 1, call_minutes: 0.5, est_cost_usd: 0.001 },
    },
  });
  assert.deepEqual(rows, frozen);
});

test("production bridge and scheduler contain all three LM-7 recording points", () => {
  const server = fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
  const scheduler = fs.readFileSync(path.join(__dirname, "../scheduler.js"), "utf8");
  assert.match(server, /kind:\s*["']telnyx_call["']/);
  assert.match(server, /kind:\s*["']gemini_live["']/);
  assert.match(scheduler, /recordDailyComposioPoll/);
});

test("normalizeApiCostEvent maps one known estimate without metadata leakage", () => {
  const row = {
    id: 42, ts: "2026-08-10T01:02:03Z", uid: "u1", kind: "gemini_live",
    quantity: 90, unit: "seconds", est_usd: "0.0345", meta: { secret: "META_SENTINEL" },
  };
  const before = structuredClone(row);

  assert.deepEqual(ledger().normalizeApiCostEvent(row), {
    schema_version: 1,
    source_ledger: "lm_api_cost",
    source_event_id: "lm_api_cost:42",
    occurred_at: "2026-08-10T01:02:03.000Z",
    owner_id: "u1",
    financial_unit_id: "life_manager_saas",
    attribution_status: "attributed",
    event_type: "operating_cost_estimate",
    cost_kind: "gemini_live",
    quantity: { value: "90", unit: "seconds" },
    amount: { value: "0.0345", currency: "USD" },
    evidence_status: "locally_estimated",
  });
  assert.deepEqual(row, before);
  assert.doesNotMatch(JSON.stringify(ledger().normalizeApiCostEvent(row)), /META_SENTINEL|secret|meta/i);
});
test("normalizeApiCostEvent leaves an unknown valid kind unattributed", () => {
  const event = ledger().normalizeApiCostEvent({
    id: "43", ts: "2026-08-10T01:02:04Z", uid: null, kind: "future_cost",
    quantity: "1", unit: "call", est_usd: 0, meta: {},
  });
  assert.equal(event.cost_kind, "future_cost");
  assert.equal(event.financial_unit_id, null);
  assert.equal(event.attribution_status, "unattributed");
  assert.equal(event.owner_id, null);
  assert.equal(event.amount.value, "0");
});
test("normalizeApiCostEvent rejects invalid identity and money with redacted errors", () => {
  const valid = {
    id: 44, ts: "2026-08-10T01:02:05Z", uid: "u1", kind: "telnyx_call",
    quantity: 1, unit: "seconds", est_usd: 0.001, meta: {},
  };
  const cases = [
    ["id", 0], ["quantity", -1], ["quantity", Number.NaN],
    ["est_usd", -1], ["est_usd", Number.POSITIVE_INFINITY],
    ["est_usd", "AMOUNT_SENTINEL"], ["unit", ""],
  ];
  for (const [field, value] of cases) {
    assert.throws(
      () => ledger().normalizeApiCostEvent({ ...valid, [field]: value }),
      (error) => /^cfo_business_ledger_invalid:[a-z_]+$/.test(error.message)
        && !/AMOUNT_SENTINEL|u1|0\.001/.test(error.message),
      field,
    );
  }
});

test("normalizeGeminiUsageEvidence maps provider counts without content", () => {
  const response = { responseId: "provider-response-id", modelVersion: "gemini-2.5-flash-001", usageMetadata: {
    promptTokenCount: 100, candidatesTokenCount: 40, totalTokenCount: 148, cachedContentTokenCount: 20,
    thoughtsTokenCount: 5, toolUsePromptTokenCount: 3,
  }, candidates: [{ text: "CANDIDATE_SENTINEL" }], unknown: "UNKNOWN_SENTINEL" };
  const context = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "11111111111111111111111111111111", request_model: "gemini-2.5-flash", ignored: "CONTEXT_SENTINEL" };
  const before = { response: structuredClone(response), context: structuredClone(context) };
  const expected = { schema_version: 1, provider: "gcp.gemini", provider_request_id: "provider-response-id", usage_sequence: 0, occurred_at: "2026-08-10T01:02:03.000Z", owner_id: "u1", financial_unit_id: "life_manager_saas", trace_id: "11111111111111111111111111111111", request_model: "gemini-2.5-flash", response_model: "gemini-2.5-flash-001", tokens: { input: 100, output: 40, cached_input: 20, reasoning_output: 5, tool_input: 3, total: 148 }, evidence_status: "provider_reported", otel_attributes: {
    "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": "gemini-2.5-flash", "gen_ai.response.id": "provider-response-id", "gen_ai.response.model": "gemini-2.5-flash-001", "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 45, "gen_ai.usage.cache_read.input_tokens": 20, "gen_ai.usage.reasoning.output_tokens": 5, "server.address": "generativelanguage.googleapis.com", "server.port": 443,
  } };
  const actual = ledger().normalizeGeminiUsageEvidence(response, context);
  assert.deepEqual(actual, expected);
  assert.doesNotMatch(JSON.stringify(actual), /CANDIDATE_SENTINEL|UNKNOWN_SENTINEL|CONTEXT_SENTINEL/);
  assert.deepEqual(response, before.response);
  assert.deepEqual(context, before.context);
  assert.deepEqual(ledger().normalizeGeminiUsageEvidence(response, context), actual);
});

test("normalizeGeminiUsageEvidence preserves zero, omits missing optionals, and redacts invalid input", () => {
  const response = { responseId: "r0", modelVersion: "m0", usageMetadata: { promptTokenCount: 0, candidatesTokenCount: 0, totalTokenCount: 0 } };
  const context = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03Z", trace_id: "22222222222222222222222222222222", request_model: "m0" };
  const zero = ledger().normalizeGeminiUsageEvidence(response, context);
  assert.deepEqual(zero.tokens, { input: 0, output: 0, cached_input: null, reasoning_output: null, tool_input: null, total: 0 });
  assert.equal(zero.otel_attributes["gen_ai.usage.input_tokens"], 0);
  assert.equal(zero.otel_attributes["gen_ai.usage.output_tokens"], 0);
  assert.ok(!("gen_ai.usage.cache_read.input_tokens" in zero.otel_attributes) && !("gen_ai.usage.reasoning.output_tokens" in zero.otel_attributes));
  const optionalZero = ledger().normalizeGeminiUsageEvidence({ ...response, usageMetadata: { ...response.usageMetadata, cachedContentTokenCount: 0, thoughtsTokenCount: 0 } }, context).otel_attributes;
  assert.equal(optionalZero["gen_ai.usage.cache_read.input_tokens"], 0);
  assert.equal(optionalZero["gen_ai.usage.reasoning.output_tokens"], 0);
  const cases = [
    ["missing id", { drop: "id" }], ["missing model", { drop: "model" }], ["missing count", { drop: "count" }],
    ["id", { response: { responseId: " " } }], ["model", { response: { modelVersion: "" } }],
    ["count", { usage: { promptTokenCount: "SENTINEL" } }], ["negative", { usage: { candidatesTokenCount: -1 } }],
    ["fraction", { usage: { totalTokenCount: 1.5 } }], ["nan", { usage: { promptTokenCount: NaN } }],
    ["infinite", { usage: { promptTokenCount: Infinity } }], ["unsafe", { usage: { promptTokenCount: Number.MAX_SAFE_INTEGER + 1 } }],
    ["sum", { usage: { candidatesTokenCount: Number.MAX_SAFE_INTEGER, thoughtsTokenCount: 1 } }],
    ["timestamp", { context: { occurred_at: "not-a-time" } }], ["trace", { context: { trace_id: "0".repeat(32) } }],
    ["owner", { context: { owner_id: " " } }], ["request", { context: { request_model: "" } }],
    ["unit", { context: { financial_unit_id: "other" } }],
  ];
  for (const [label, patch] of cases) {
    const value = { ...response, usageMetadata: { ...response.usageMetadata, ...(patch.usage || {}) }, ...(patch.response || {}) };
    const metadata = { ...context, ...(patch.context || {}) };
    if (patch.drop === "id") delete value.responseId;
    if (patch.drop === "model") delete value.modelVersion;
    if (patch.drop === "count") delete value.usageMetadata.promptTokenCount;
    assert.throws(() => ledger().normalizeGeminiUsageEvidence(value, metadata), (error) => /^cfo_provider_usage_invalid:[a-z_]+$/.test(error.message) && !/SENTINEL/.test(error.message), label);
  }
});

test("normalizeGeminiLiveUsageEvidence maps one Live message without content", () => {
  const message = { usageMetadata: { promptTokenCount: 515, responseTokenCount: 38, totalTokenCount: 560, cachedContentTokenCount: 2, thoughtsTokenCount: 5, toolUsePromptTokenCount: 1 }, serverContent: { outputTranscription: { text: "LIVE_OUTPUT_SENTINEL" } } };
  const context = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "1".repeat(32), request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025", live_session_id: "2".repeat(32), usage_sequence: 7 };
  const before = { message: structuredClone(message), context: structuredClone(context) };
  const expected = { schema_version: 1, provider: "gcp.gemini", provider_request_id: null, local_correlation_id: `live-session:${context.live_session_id}`, usage_sequence: 7, occurred_at: "2026-08-10T01:02:03.000Z", owner_id: "u1", financial_unit_id: "life_manager_saas", trace_id: "1".repeat(32), request_model: context.request_model, response_model: null, tokens: { input: 515, output: 38, cached_input: 2, reasoning_output: 5, tool_input: 1, total: 560 }, evidence_status: "provider_reported", otel_attributes: { "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": context.request_model, "gen_ai.request.stream": true, "gen_ai.output.type": "speech", "gen_ai.usage.input_tokens": 515, "gen_ai.usage.output_tokens": 43, "gen_ai.usage.cache_read.input_tokens": 2, "gen_ai.usage.reasoning.output_tokens": 5, "server.address": "generativelanguage.googleapis.com", "server.port": 443 } };
  const actual = ledger().normalizeGeminiLiveUsageEvidence(message, context);
  assert.deepEqual(actual, expected);
  assert.doesNotMatch(JSON.stringify(actual), /LIVE_OUTPUT_SENTINEL|gen_ai\.response\./);
  assert.deepEqual({ message, context }, before);
  assert.deepEqual(ledger().normalizeGeminiLiveUsageEvidence(message, context), actual);
});

test("normalizeGeminiLiveUsageEvidence preserves optional absence and redacts invalid input", () => {
  const base = { message: { usageMetadata: { promptTokenCount: 0, responseTokenCount: 0, totalTokenCount: 0 } }, context: { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03Z", trace_id: "1".repeat(32), request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025", live_session_id: "2".repeat(32), usage_sequence: 0 } };
  const zero = ledger().normalizeGeminiLiveUsageEvidence(base.message, base.context);
  assert.deepEqual(zero.tokens, { input: 0, output: 0, cached_input: null, reasoning_output: null, tool_input: null, total: 0 });
  assert.equal(zero.otel_attributes["gen_ai.usage.output_tokens"], 0);
  assert.ok(!("gen_ai.usage.cache_read.input_tokens" in zero.otel_attributes) && !("gen_ai.usage.reasoning.output_tokens" in zero.otel_attributes));
  const optionalZero = ledger().normalizeGeminiLiveUsageEvidence({ ...base.message, usageMetadata: { ...base.message.usageMetadata, cachedContentTokenCount: 0, thoughtsTokenCount: 0, toolUsePromptTokenCount: 0 } }, base.context);
  assert.deepEqual(optionalZero.tokens, { input: 0, output: 0, cached_input: 0, reasoning_output: 0, tool_input: 0, total: 0 });
  assert.equal(optionalZero.otel_attributes["gen_ai.usage.cache_read.input_tokens"], 0); assert.equal(optionalZero.otel_attributes["gen_ai.usage.reasoning.output_tokens"], 0);
  const cases = [
    ["missing_count", (m) => delete m.usageMetadata.responseTokenCount], ["negative", (m) => { m.usageMetadata.responseTokenCount = -1; }], ["string", (m) => { m.usageMetadata.totalTokenCount = "SENTINEL"; }], ["unsafe", (m) => { m.usageMetadata.promptTokenCount = Number.MAX_SAFE_INTEGER + 1; }], ["overflow", (m) => { m.usageMetadata.responseTokenCount = Number.MAX_SAFE_INTEGER; m.usageMetadata.thoughtsTokenCount = 1; }],
    ["session", (_, c) => { c.live_session_id = "0".repeat(32); }], ["sequence", (_, c) => { c.usage_sequence = 1.5; }], ["model", (_, c) => { c.request_model = "gemini-2.5-flash"; }], ["trace", (_, c) => { c.trace_id = "0".repeat(32); }],
  ];
  for (const [label, mutate] of cases) { const value = structuredClone(base); mutate(value.message, value.context); assert.throws(() => ledger().normalizeGeminiLiveUsageEvidence(value.message, value.context), (error) => /^cfo_provider_usage_invalid:[a-z_]+$/.test(error.message) && !/SENTINEL|not-hex/.test(error.message), label); }
});

const localAgentInput = (overrides = {}, tokenOverrides = {}) => ({
  version: 1, event_id: "0123456789abcdef01234567", timestamp: "2026-08-10T01:02:03+09:00",
  loop: "morning-loop", task_label: "daily-brief", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null,
  attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 120, cached_input: 10, cache_creation_input: 4, output: 80, reasoning_output: 30, total: 234, ...tokenOverrides }, ...overrides,
});
const SOURCE_ROW_REF = "1".repeat(64), OTHER_SOURCE_ROW_REF = "2".repeat(64);
const localAgentContext = (source_row_ref = SOURCE_ROW_REF, financial_unit_id = null) => ({ source_row_ref, financial_unit_id });
const localAgentPair = (source, overrides = {}, tokens = {}) => ({ input: localAgentInput(overrides, tokens), context: localAgentContext(source) });

test("normalizeLocalAgentUsageEvent preserves runner values, provenance, attribution, and freeze", () => {
  const input = localAgentInput({ raw_session_ref: "ignored" });
  const event = ledger().normalizeLocalAgentUsageEvent(input, localAgentContext(SOURCE_ROW_REF, "life_manager_saas"));
  assert.deepEqual(event, { schema_version: 1, source_ledger: "local_agent_usage", source_event_id: `local_agent_usage:${SOURCE_ROW_REF}`, runner_event_id: "0123456789abcdef01234567", occurred_at: "2026-08-09T16:02:03.000Z", provider: "codex", provider_name: "openai", request_model: "gpt-5.6", upstream_model: null, run: { loop: "morning-loop", task_label: "daily-brief", attempt: 1, status: "success" }, financial_unit_id: "life_manager_saas", attribution_status: "attributed", measurement: "provider_reported", token_value_basis: "runner_normalized_provider_usage", tokens: { input: 120, cached_input: 10, cache_creation_input: 4, output: 80, reasoning_output: 30, total: 234 }, coverage_status: "covered" });
  assert.deepEqual(input, localAgentInput({ raw_session_ref: "ignored" }));
  assert.equal("raw_session_ref" in event, false);
  assert.ok(Object.isFrozen(event) && Object.isFrozen(event.tokens) && Object.isFrozen(event.run));
});

test("normalizeLocalAgentUsageEvent preserves provider variants and missing usage truth", () => {
  const claude = ledger().normalizeLocalAgentUsageEvent(localAgentInput({ event_id: "fedcba9876543210fedcba98", provider: "claude", provider_name: "anthropic", model: "claude-sonnet", upstream_model: "claude-sonnet-4-20250514" }, { cached_input: 60, cache_creation_input: 20 }), localAgentContext());
  assert.deepEqual({ provider: claude.provider, provider_name: claude.provider_name, request_model: claude.request_model, upstream_model: claude.upstream_model, cache: [claude.tokens.cached_input, claude.tokens.cache_creation_input], financial_unit_id: claude.financial_unit_id, attribution_status: claude.attribution_status }, { provider: "claude", provider_name: "anthropic", request_model: "claude-sonnet", upstream_model: "claude-sonnet-4-20250514", cache: [60, 20], financial_unit_id: null, attribution_status: "unattributed" });
  const api = ledger().normalizeLocalAgentUsageEvent(localAgentInput({ event_id: "aaaaaaaaaaaaaaaaaaaaaaaa", provider: "openai-api" }), localAgentContext());
  assert.equal(api.provider, "openai-api");
  const unavailable = ledger().normalizeLocalAgentUsageEvent(localAgentInput({ event_id: "bbbbbbbbbbbbbbbbbbbbbbbb", status: "failed", measurement: "unavailable" }, { input: null, cached_input: null, cache_creation_input: null, output: null, reasoning_output: null, total: null }), localAgentContext(SOURCE_ROW_REF, "life_manager_saas"));
  assert.deepEqual(unavailable.tokens, { input: null, cached_input: null, cache_creation_input: null, output: null, reasoning_output: null, total: null });
  assert.equal(unavailable.token_value_basis, "unavailable"); assert.equal(unavailable.coverage_status, "missing_usage");
});

test("normalizeLocalAgentUsageEvent keeps colliding runner IDs distinct by source row", () => {
  const input = localAgentInput();
  const first = ledger().normalizeLocalAgentUsageEvent(input, localAgentContext(SOURCE_ROW_REF));
  const second = ledger().normalizeLocalAgentUsageEvent(input, localAgentContext(OTHER_SOURCE_ROW_REF));
  assert.notEqual(first.source_event_id, second.source_event_id); assert.equal(first.runner_event_id, second.runner_event_id);
});

test("normalizeLocalAgentUsageEvent rejects invalid or hostile input with fixed redacted errors", () => {
  const valid = localAgentInput();
  const cases = [[[], localAgentContext()], [valid, []], [localAgentInput({ event_id: "HOSTILE_EVENT_SENTINEL" }), localAgentContext()], [localAgentInput({}, { input: null }), localAgentContext()], [localAgentInput({ status: "running" }), localAgentContext()], [localAgentInput({ measurement: "estimated" }), localAgentContext()], [localAgentInput({ measurement: "unavailable" }, { input: 0 }), localAgentContext()], [valid, { financial_unit_id: null }], [valid, localAgentContext("0".repeat(64))], [valid, localAgentContext("A".repeat(64))]];
  for (const [input, mapping] of cases) assert.throws(() => ledger().normalizeLocalAgentUsageEvent(input, mapping), (error) => /^cfo_local_agent_usage_invalid:[a-z_]+$/.test(error.message) && !/HOSTILE_EVENT_SENTINEL|valid-loop|gpt-5\.6/.test(error.message));
});
test("reduceLocalAgentUsageEvents dedupes exact source rows and freezes the receipt", () => {
  const pair = localAgentPair(SOURCE_ROW_REF), receipt = ledger().reduceLocalAgentUsageEvents([pair, structuredClone(pair)]);
  assert.deepEqual(receipt.counts, { discovered_rows: 2, accepted_rows: 1, duplicate_rows: 1, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: 0 }); assert.equal(receipt.events[0].source_event_id, `local_agent_usage:${SOURCE_ROW_REF}`); assert.deepEqual(receipt.coverage_exceptions, []);
  assert.ok(Object.isFrozen(receipt) && Object.isFrozen(receipt.events) && Object.isFrozen(receipt.counts) && Object.isFrozen(receipt.coverage_exceptions));
  assert.equal(receipt.counts.discovered_rows, receipt.counts.accepted_rows + receipt.counts.duplicate_rows + receipt.counts.conflicting_rows);
});

test("reduceLocalAgentUsageEvents excludes conflicts and is input-order independent", () => {
  const unique = localAgentPair("3".repeat(64), { event_id: "bbbbbbbbbbbbbbbbbbbbbbbb" }), conflict = localAgentPair("4".repeat(64), { event_id: "cccccccccccccccccccccccc" }), changed = localAgentPair("4".repeat(64), { event_id: "cccccccccccccccccccccccc" }, { output: 81, total: 235 }), reduce = (pairs) => ledger().reduceLocalAgentUsageEvents(pairs);
  const receipt = reduce([changed, unique, conflict]), reversed = reduce([conflict, unique, changed]);
  assert.deepEqual(receipt, reversed); assert.deepEqual(receipt.events.map((event) => event.source_event_id), [`local_agent_usage:${"3".repeat(64)}`]); assert.deepEqual(receipt.counts, { discovered_rows: 3, accepted_rows: 1, duplicate_rows: 0, conflicting_rows: 2, missing_usage_rows: 0, runner_collision_groups: 0 });
  assert.deepEqual(receipt.coverage_exceptions, ["conflicting_usage"]);
});

test("reduceLocalAgentUsageEvents preserves runner collisions and accepted missing usage", () => {
  const a = localAgentPair("5".repeat(64), { event_id: "dddddddddddddddddddddddd" }), b = localAgentPair("6".repeat(64), { event_id: "dddddddddddddddddddddddd" }), missing = localAgentPair("7".repeat(64), { event_id: "eeeeeeeeeeeeeeeeeeeeeeee", status: "failed", measurement: "unavailable" }, { input: null, cached_input: null, cache_creation_input: null, output: null, reasoning_output: null, total: null });
  const conflict = localAgentPair("8".repeat(64), { event_id: "ffffffffffffffffffffffff" }), changed = localAgentPair("8".repeat(64), { event_id: "ffffffffffffffffffffffff" }, { output: 81, total: 235 }), receipt = ledger().reduceLocalAgentUsageEvents([changed, missing, b, structuredClone(missing), conflict, a]);
  assert.deepEqual(receipt.counts, { discovered_rows: 6, accepted_rows: 3, duplicate_rows: 1, conflicting_rows: 2, missing_usage_rows: 1, runner_collision_groups: 1 }); assert.deepEqual(receipt.coverage_exceptions, ["conflicting_usage", "missing_usage", "runner_identity_collision"]); assert.deepEqual(receipt.events.map((event) => event.source_event_id), ["5", "6", "7"].map((id) => `local_agent_usage:${id.repeat(64)}`));
});

test("reduceLocalAgentUsageEvents rejects non-dense or non-exact hostile pairs with redacted errors", () => {
  const valid = localAgentPair(SOURCE_ROW_REF), hostile = { ...valid, leak: "HOSTILE_SENTINEL" };
  for (const pairs of [null, {}, [hostile], [, valid], [{ input: localAgentInput({ event_id: "HOSTILE_EVENT_SENTINEL" }), context: localAgentContext(SOURCE_ROW_REF) }]]) {
    assert.throws(() => ledger().reduceLocalAgentUsageEvents(pairs), (error) => /^cfo_local_agent_usage_invalid:[a-z_]+$/.test(error.message) && !/HOSTILE_SENTINEL|HOSTILE_EVENT_SENTINEL|gpt-5\.6/.test(error.message));
  }
});
