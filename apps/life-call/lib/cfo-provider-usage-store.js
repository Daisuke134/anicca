"use strict";
const { normalizeGeminiUsageEvidence, normalizeGeminiLiveUsageEvidence } = require("./ledger.js");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const ERROR_PREFIX = "cfo_provider_usage_store_failed:", PROVIDER_RECEIPT_KEYS = new Set(["public_ref", "provider", "provider_request_id", "usage_sequence", "trace_id", "created_at"]), LIVE_RECEIPT_KEYS = new Set(["public_ref", "provider", "local_correlation_id", "usage_sequence", "trace_id", "created_at"]);
const { fail, internal, exact, uuid, timestamp, validateOptions, freeze, postRpc } = createCfoSupabaseRpc(ERROR_PREFIX);
function receipt(value, expected) {
  const local = expected.provider_request_id === null, identity = local ? "local_correlation_id" : "provider_request_id";
  exact(value, local ? LIVE_RECEIPT_KEYS : PROVIDER_RECEIPT_KEYS, "invalid_receipt"); const public_ref = uuid(value.public_ref, "invalid_receipt");
  if (!timestamp(value.created_at)) fail("invalid_receipt");
  if (value.provider !== expected.provider || value[identity] !== expected[identity] || value.usage_sequence !== expected.usage_sequence || value.trace_id !== expected.trace_id) fail("receipt_mismatch");
  try { return freeze(structuredClone(local ? { public_ref, provider: value.provider, local_correlation_id: value.local_correlation_id, usage_sequence: value.usage_sequence, trace_id: value.trace_id, created_at: value.created_at } : { public_ref, provider: value.provider, provider_request_id: value.provider_request_id, usage_sequence: value.usage_sequence, trace_id: value.trace_id, created_at: value.created_at })); } catch { fail("invalid_receipt"); }
}
function rpcBody(evidence) {
  const t = evidence.tokens, body = { p_uid: evidence.owner_id, p_financial_unit_id: evidence.financial_unit_id, p_attribution_status: "attributed", p_provider: evidence.provider, p_provider_request_id: evidence.provider_request_id, p_usage_sequence: evidence.usage_sequence, p_occurred_at: evidence.occurred_at, p_trace_id: evidence.trace_id, p_request_model: evidence.request_model, p_response_model: evidence.response_model, p_input_tokens: t.input, p_output_tokens: t.output, p_total_tokens: t.total, p_cached_input_tokens: t.cached_input, p_reasoning_output_tokens: t.reasoning_output, p_tool_input_tokens: t.tool_input, p_evidence_status: evidence.evidence_status };
  if (Object.prototype.hasOwnProperty.call(evidence, "local_correlation_id")) body.p_local_correlation_id = evidence.local_correlation_id;
  return body;
}
async function appendGeminiUsageEvidence(response, context, options = {}) {
  let evidence, config;
  try { evidence = normalizeGeminiUsageEvidence(response, context); config = validateOptions(options); } catch (error) { if (internal(error)) throw error; fail("invalid_input"); }
  return receipt(await postRpc(config, "lm_append_cfo_model_usage_evidence", rpcBody(evidence)), evidence);
}
async function appendGeminiLiveUsageEvidence(message, context, options = {}) {
  let evidence, config;
  try { evidence = normalizeGeminiLiveUsageEvidence(message, context); config = validateOptions(options); } catch (error) { if (internal(error)) throw error; fail("invalid_input"); }
  return receipt(await postRpc(config, "lm_append_cfo_model_usage_evidence", rpcBody(evidence)), evidence);
}
module.exports = { appendGeminiUsageEvidence, appendGeminiLiveUsageEvidence };
