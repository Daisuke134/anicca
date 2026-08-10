"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { appendGeminiUsageEvidence, appendGeminiLiveUsageEvidence } = require("./cfo-provider-usage-store.js");
const URL = "https://project.supabase.co", KEY = "service-role-fixture";
const RESPONSE = { responseId: "provider-response-id", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 4, totalTokenCount: 99, thoughtsTokenCount: 0 }, candidates: [{ text: "CONTENT_SENTINEL" }], unknown: "RAW_SENTINEL" };
const CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "11111111111111111111111111111111", request_model: "gemini-2.5-flash" };
const RECEIPT = { public_ref: "30000000-0000-4000-8000-000000000001", provider: "gcp.gemini", provider_request_id: "provider-response-id", usage_sequence: 0, trace_id: CONTEXT.trace_id, created_at: "2026-08-10T01:02:04.000Z" };
const LIVE_MESSAGE = { usageMetadata: { promptTokenCount: 515, responseTokenCount: 38, totalTokenCount: 560, cachedContentTokenCount: 2, thoughtsTokenCount: 5, toolUsePromptTokenCount: 1 }, serverContent: { outputTranscription: { text: "LIVE_OUTPUT_SENTINEL" } } };
const LIVE_CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "11111111111111111111111111111111", request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025", live_session_id: "22222222222222222222222222222222", usage_sequence: 7 };
const LIVE_RECEIPT = { public_ref: "30000000-0000-4000-8000-000000000002", provider: "gcp.gemini", local_correlation_id: "live-session:22222222222222222222222222222222", usage_sequence: 7, trace_id: LIVE_CONTEXT.trace_id, created_at: "2026-08-10T01:02:04.000Z" };
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

test("maps one Gemini Live usage fact to one exact RPC and local receipt", async () => {
  const calls = [], liveReceipt = { ...LIVE_RECEIPT }, fetchImpl = async (url, init) => { calls.push({ url, init }); return http(liveReceipt); };
  const message = structuredClone(LIVE_MESSAGE), context = structuredClone(LIVE_CONTEXT), before = { message: structuredClone(message), context: structuredClone(context) };
  const value = await appendGeminiLiveUsageEvidence(message, context, { supaUrl: URL, supaKey: KEY, fetchImpl });
  assert.equal(calls.length, 1); assert.equal(calls[0].url, `${URL}/rest/v1/rpc/lm_append_cfo_model_usage_evidence`);
  assert.deepEqual(calls[0].init.headers, { apikey: KEY, Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_uid: "u1", p_financial_unit_id: "life_manager_saas", p_attribution_status: "attributed", p_provider: "gcp.gemini", p_provider_request_id: null, p_usage_sequence: 7, p_occurred_at: LIVE_CONTEXT.occurred_at, p_trace_id: LIVE_CONTEXT.trace_id, p_request_model: LIVE_CONTEXT.request_model, p_response_model: null, p_input_tokens: 515, p_output_tokens: 38, p_total_tokens: 560, p_cached_input_tokens: 2, p_reasoning_output_tokens: 5, p_tool_input_tokens: 1, p_evidence_status: "provider_reported", p_local_correlation_id: LIVE_RECEIPT.local_correlation_id });
  assert.doesNotMatch(calls[0].init.body, /LIVE_OUTPUT_SENTINEL|otel_attributes|schema_version/);
  assert.deepEqual(value, LIVE_RECEIPT); assert.equal(Object.isFrozen(value), true); assert.ok(!("provider_request_id" in value)); assert.doesNotMatch(JSON.stringify(value), /LIVE_OUTPUT_SENTINEL/);
  liveReceipt.trace_id = "22222222222222222222222222222222"; assert.deepEqual(value, LIVE_RECEIPT); assert.deepEqual({ message, context }, before);
});

test("fails closed on Live input and receipt identity boundaries without retry or logs", async () => {
  const original = [console.log, console.error, console.warn]; let calls = 0, logs = 0; console.log = console.error = console.warn = () => { logs += 1; };
  const run = (body, pattern) => rejects(() => appendGeminiLiveUsageEvidence(LIVE_MESSAGE, LIVE_CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; return http(body); } }), pattern);
  try {
    await rejects(() => appendGeminiLiveUsageEvidence({ usageMetadata: {} }, LIVE_CONTEXT, { supaUrl: URL, supaKey: KEY, fetchImpl: async () => { calls += 1; } }), /^cfo_provider_usage_store_failed:invalid_input$/);
    await run({ ...LIVE_RECEIPT, local_correlation_id: "live-session:33333333333333333333333333333333" }, /^cfo_provider_usage_store_failed:receipt_mismatch$/);
    await run({ ...LIVE_RECEIPT, trace_id: "33333333333333333333333333333333" }, /^cfo_provider_usage_store_failed:receipt_mismatch$/);
    await run({ ...LIVE_RECEIPT, provider_request_id: "provider-response-id" }, /^cfo_provider_usage_store_failed:invalid_receipt$/);
    await run({ ...LIVE_RECEIPT, extra: "LIVE_OUTPUT_SENTINEL" }, /^cfo_provider_usage_store_failed:invalid_receipt$/);
  } finally { [console.log, console.error, console.warn] = original; }
  assert.equal(calls, 4); assert.equal(logs, 0);
});
