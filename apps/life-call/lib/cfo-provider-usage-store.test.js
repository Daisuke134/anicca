"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { appendGeminiUsageEvidence } = require("./cfo-provider-usage-store.js");
const URL = "https://project.supabase.co", KEY = "service-role-fixture";
const RESPONSE = { responseId: "provider-response-id", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 4, totalTokenCount: 99, thoughtsTokenCount: 0 }, candidates: [{ text: "CONTENT_SENTINEL" }], unknown: "RAW_SENTINEL" };
const CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "11111111111111111111111111111111", request_model: "gemini-2.5-flash" };
const RECEIPT = { public_ref: "30000000-0000-4000-8000-000000000001", provider: "gcp.gemini", provider_request_id: "provider-response-id", usage_sequence: 0, trace_id: CONTEXT.trace_id, created_at: "2026-08-10T01:02:04.000Z" };
const http = (body = RECEIPT, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const rejects = (call, pattern) => assert.rejects(call, error => { assert.match(error.message, pattern); return true; });

test("maps one normalized Gemini usage fact to one exact RPC", async () => {
  const calls = [], providerReceipt = { ...RECEIPT }, fetchImpl = async (url, init) => { calls.push({ url, init }); return http(providerReceipt); };
  const value = await appendGeminiUsageEvidence(RESPONSE, CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 1); assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_model_usage_evidence`);
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: "u1", p_financial_unit_id: "life_manager_saas", p_attribution_status: "attributed", p_provider: "gcp.gemini", p_provider_request_id: "provider-response-id", p_usage_sequence: 0, p_occurred_at: CONTEXT.occurred_at, p_trace_id: CONTEXT.trace_id, p_request_model: CONTEXT.request_model, p_response_model: "gemini-2.5-flash-001", p_input_tokens: 10, p_output_tokens: 4, p_total_tokens: 99, p_cached_input_tokens: null, p_reasoning_output_tokens: 0, p_tool_input_tokens: null, p_evidence_status: "provider_reported" });
  assert.doesNotMatch(calls[0].init.body, /CONTENT_SENTINEL|RAW_SENTINEL|otel_attributes|schema_version/); assert.deepEqual(value, RECEIPT); assert.equal(Object.isFrozen(value), true);
  providerReceipt.trace_id = "22222222222222222222222222222222"; assert.deepEqual(value, RECEIPT);
});

test("rejects invalid provider input before fetch", async () => {
  let calls = 0; const invalid = { ...RESPONSE }; delete invalid.responseId;
  await rejects(() => appendGeminiUsageEvidence(invalid, CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; } }), /^cfo_provider_usage_store_failed:invalid_input$/); assert.equal(calls, 0);
});

test("fails closed on receipt and transport boundaries without retry or logs", async () => {
  const original = [console.log, console.error, console.warn]; let logs = 0, calls = 0, jsonCalls = 0;
  console.log = console.error = console.warn = () => { logs += 1; };
  const run = (fetchImpl, pattern) => rejects(() => appendGeminiUsageEvidence(RESPONSE, CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl: async (...args) => { calls += 1; return fetchImpl(...args); } }), pattern);
  try {
    await run(async () => http({ ...RECEIPT, provider_request_id: "other-response" }), /^cfo_provider_usage_store_failed:receipt_mismatch$/);
    await run(async () => http({ ...RECEIPT, extra: "RAW_SENTINEL" }), /^cfo_provider_usage_store_failed:invalid_receipt$/);
    await run(async () => { throw new Error("CONTENT_SENTINEL"); }, /^cfo_provider_usage_store_failed:network$/);
    await run(async () => ({ ok: false, status: 409, json: () => { jsonCalls += 1; throw new Error("RAW_SENTINEL"); } }), /^cfo_provider_usage_store_failed:provider_409$/);
  } finally { [console.log, console.error, console.warn] = original; }
  assert.equal(calls, 4); assert.equal(jsonCalls, 0); assert.equal(logs, 0);
});
