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
    "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": "gemini-2.5-flash", "gen_ai.response.id": "provider-response-id", "gen_ai.response.model": "gemini-2.5-flash-001", "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 45, "gen_ai.usage.cache_read.input_tokens": 20, "gen_ai.usage.reasoning.output_tokens": 5, "server.address": "generativelanguage.googleapis.com",
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
