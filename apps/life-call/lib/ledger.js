"use strict";

const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { canonicalJson } = require("./cfo-registry.js");
const { fail: costEventFail, plain: plainCostRow, timestamp: validCostTimestamp } = createCfoSupabaseRpc("cfo_business_ledger_invalid:");
const { fail: usageFail, internal: usageInternal, plain: plainUsageInput, timestamp: validUsageTimestamp } = createCfoSupabaseRpc("cfo_provider_usage_invalid:");
const { exact: exactLocalAgentUsage, fail: localAgentUsageFail, freeze: freezeLocalAgentUsage, internal: localAgentUsageInternal, plain: plainLocalAgentUsageInput, timestamp: validLocalAgentUsageTimestamp } = createCfoSupabaseRpc("cfo_local_agent_usage_invalid:");
const LOCAL_AGENT_PAIR_KEYS = new Set(["input", "context"]);

function headers(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

// Best-effort cost persistence. Ledger failures must never break a call or scheduler tick.
async function recordCost({ uid, kind, quantity, unit, estUsd, meta } = {}, opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const log = opts.log || console.error;
  try {
    if (!supaUrl || !supaKey || !kind || typeof fetchImpl !== "function") {
      throw new Error("Supabase credentials or ledger kind missing");
    }
    const response = await fetchImpl(`${supaUrl}/rest/v1/lm_api_cost`, {
      method: "POST",
      headers: headers(supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
      body: JSON.stringify({
        uid: uid == null ? null : String(uid),
        kind: String(kind),
        quantity: Number(quantity) || 0,
        unit: unit == null ? null : String(unit),
        est_usd: Number(estUsd) || 0,
        meta: meta == null ? {} : meta,
      }),
    });
    if (!response.ok) throw new Error(`Supabase insert failed (${response.status})`);
    return true;
  } catch (error) {
    log("[ledger] recordCost failed", error && error.message ? error.message : error);
    return false;
  }
}

// DB-backed daily aggregation: every process/tick asks Supabase whether today's per-user row exists.
// No process-memory counter is authoritative, so restarts cannot create a fresh daily bucket.
async function recordDailyComposioPoll(uid, opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const log = opts.log || console.error;
  try {
    if (!supaUrl || !supaKey || !uid || typeof fetchImpl !== "function") {
      throw new Error("Supabase credentials or uid missing");
    }
    const now = new Date(opts.nowMs == null ? Date.now() : opts.nowMs);
    const dayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const nextDay = new Date(dayStart.getTime() + 86400000);
    const query = [
      `uid=eq.${encodeURIComponent(uid)}`,
      "kind=eq.composio_poll",
      `ts=gte.${encodeURIComponent(dayStart.toISOString())}`,
      `ts=lt.${encodeURIComponent(nextDay.toISOString())}`,
      "select=id",
      "limit=1",
    ].join("&");
    const response = await fetchImpl(`${supaUrl}/rest/v1/lm_api_cost?${query}`, {
      headers: headers(supaKey),
    });
    if (!response.ok) throw new Error(`Supabase daily lookup failed (${response.status})`);
    const rows = await response.json().catch(() => []);
    if (Array.isArray(rows) && rows.length > 0) return false;
    return recordCost({
      uid, kind: "composio_poll", quantity: 1, unit: "day", estUsd: 0,
      meta: { day: dayStart.toISOString().slice(0, 10) },
    }, { supaUrl, supaKey, fetchImpl, log });
  } catch (error) {
    log("[ledger] composio daily aggregation failed", error && error.message ? error.message : error);
    return false;
  }
}

async function monthlyComposioCallCount(opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const log = opts.log || console.error;
  try {
    if (!supaUrl || !supaKey || typeof fetchImpl !== "function") return null;
    const now = new Date(opts.nowMs == null ? Date.now() : opts.nowMs);
    const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    const nextMonth = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1));
    const query = ["select=id", "kind=eq.composio_call",
      `ts=gte.${encodeURIComponent(monthStart.toISOString())}`,
      `ts=lt.${encodeURIComponent(nextMonth.toISOString())}`, "limit=1"].join("&");
    const response = await fetchImpl(`${supaUrl}/rest/v1/lm_api_cost?${query}`, {
      headers: headers(supaKey, { Prefer: "count=exact" }),
    });
    if (!response.ok) throw new Error(`Supabase monthly count failed (${response.status})`);
    const range = response.headers && response.headers.get("content-range");
    const match = String(range || "").match(/\/(\d+)$/);
    return match ? Number(match[1]) : 0;
  } catch (error) {
    log("[ledger] monthly Composio count failed", error && error.message ? error.message : error);
    return null;
  }
}

const DIRECT_COST_KINDS = new Set(["gemini_live", "telnyx_call", "composio_call", "composio_poll"]);
const COST_KIND = /^[a-z][a-z0-9_]*$/;
const NUMERIC_TEXT = /^(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/;

function positiveId(value) {
  if (typeof value === "number" && Number.isSafeInteger(value) && value > 0) return String(value);
  if (typeof value === "string" && /^[1-9]\d*$/.test(value)) return value;
  costEventFail("invalid_id");
}

function numericText(value, reason) {
  if (typeof value !== "number" && typeof value !== "string") costEventFail(reason);
  const text = String(value);
  if (!NUMERIC_TEXT.test(text) || !Number.isFinite(Number(text)) || Number(text) < 0) costEventFail(reason);
  return text;
}

function normalizeApiCostEvent(row) {
  if (!plainCostRow(row)) costEventFail("invalid_row");
  const id = positiveId(row.id);
  if (!validCostTimestamp(row.ts)) costEventFail("invalid_timestamp");
  const ownerId = row.uid === null ? null : row.uid;
  if (ownerId !== null && (typeof ownerId !== "string" || ownerId.length === 0 || ownerId.trim() !== ownerId))
    costEventFail("invalid_owner");
  if (typeof row.kind !== "string" || !COST_KIND.test(row.kind)) costEventFail("invalid_kind");
  if (typeof row.unit !== "string" || row.unit.length === 0 || row.unit.trim() !== row.unit)
    costEventFail("invalid_unit");
  const attributed = DIRECT_COST_KINDS.has(row.kind);
  return {
    schema_version: 1, source_ledger: "lm_api_cost", source_event_id: `lm_api_cost:${id}`,
    occurred_at: new Date(row.ts).toISOString(), owner_id: ownerId,
    financial_unit_id: attributed ? "life_manager_saas" : null,
    attribution_status: attributed ? "attributed" : "unattributed",
    event_type: "operating_cost_estimate", cost_kind: row.kind,
    quantity: { value: numericText(row.quantity, "invalid_quantity"), unit: row.unit },
    amount: { value: numericText(row.est_usd, "invalid_amount"), currency: "USD" },
    evidence_status: "locally_estimated",
  };
}

function usageString(value, reason) {
  if (typeof value !== "string" || value.length === 0 || value.trim() !== value) usageFail(reason);
  return value;
}

function providerCount(metadata, key, optional) {
  if (optional && !Object.prototype.hasOwnProperty.call(metadata, key)) return null;
  const value = metadata[key];
  if (!Number.isSafeInteger(value) || value < 0) usageFail("invalid_count");
  return value;
}

function normalizeGeminiUsageEvidence(response, context) {
  try {
    if (!plainUsageInput(response) || !plainUsageInput(context) || !plainUsageInput(response.usageMetadata)) usageFail("invalid_input");
    const metadata = response.usageMetadata;
    const providerRequestId = usageString(response.responseId, "invalid_response_id");
    const responseModel = usageString(response.modelVersion, "invalid_response_model");
    const input = providerCount(metadata, "promptTokenCount", false);
    const output = providerCount(metadata, "candidatesTokenCount", false);
    const total = providerCount(metadata, "totalTokenCount", false);
    const cached = providerCount(metadata, "cachedContentTokenCount", true);
    const reasoning = providerCount(metadata, "thoughtsTokenCount", true);
    const tool = providerCount(metadata, "toolUsePromptTokenCount", true);
    const owner = usageString(context.owner_id, "invalid_owner");
    const requestModel = usageString(context.request_model, "invalid_request_model");
    if (context.financial_unit_id !== "life_manager_saas") usageFail("invalid_financial_unit");
    if (!validUsageTimestamp(context.occurred_at)) usageFail("invalid_timestamp");
    if (typeof context.trace_id !== "string" || !/^(?!0{32})[0-9a-f]{32}$/.test(context.trace_id)) usageFail("invalid_trace_id");
    const otelOutput = output + (reasoning === null ? 0 : reasoning);
    if (!Number.isSafeInteger(otelOutput)) usageFail("invalid_count");
    const otelAttributes = { "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": requestModel, "gen_ai.response.id": providerRequestId, "gen_ai.response.model": responseModel, "gen_ai.usage.input_tokens": input, "gen_ai.usage.output_tokens": otelOutput, "server.address": "generativelanguage.googleapis.com", "server.port": 443 };
    if (cached !== null) otelAttributes["gen_ai.usage.cache_read.input_tokens"] = cached;
    if (reasoning !== null) otelAttributes["gen_ai.usage.reasoning.output_tokens"] = reasoning;
    return { schema_version: 1, provider: "gcp.gemini", provider_request_id: providerRequestId, usage_sequence: 0, occurred_at: new Date(context.occurred_at).toISOString(), owner_id: owner, financial_unit_id: "life_manager_saas", trace_id: context.trace_id, request_model: requestModel, response_model: responseModel, tokens: { input, output, cached_input: cached, reasoning_output: reasoning, tool_input: tool, total }, evidence_status: "provider_reported", otel_attributes: otelAttributes };
  } catch (error) {
    if (usageInternal(error)) throw error;
    usageFail("invalid_input");
  }
}

function normalizeGeminiLiveUsageEvidence(message, context) {
  try {
    if (!plainUsageInput(message) || !plainUsageInput(context) || !plainUsageInput(message.usageMetadata)) usageFail("invalid_input");
    const metadata = message.usageMetadata;
    const input = providerCount(metadata, "promptTokenCount", false); const output = providerCount(metadata, "responseTokenCount", false); const total = providerCount(metadata, "totalTokenCount", false);
    const cached = providerCount(metadata, "cachedContentTokenCount", true); const reasoning = providerCount(metadata, "thoughtsTokenCount", true); const tool = providerCount(metadata, "toolUsePromptTokenCount", true);
    const owner = usageString(context.owner_id, "invalid_owner"); const requestModel = usageString(context.request_model, "invalid_request_model");
    if (requestModel !== "models/gemini-2.5-flash-native-audio-preview-09-2025") usageFail("invalid_request_model");
    if (context.financial_unit_id !== "life_manager_saas") usageFail("invalid_financial_unit");
    if (!validUsageTimestamp(context.occurred_at)) usageFail("invalid_timestamp");
    if (typeof context.trace_id !== "string" || !/^(?!0{32})[0-9a-f]{32}$/.test(context.trace_id)) usageFail("invalid_trace_id");
    const session = usageString(context.live_session_id, "invalid_live_session_id");
    if (!/^(?!0{32})[0-9a-f]{32}$/.test(session)) usageFail("invalid_live_session_id");
    if (!Number.isSafeInteger(context.usage_sequence) || context.usage_sequence < 0) usageFail("invalid_usage_sequence");
    const otelOutput = output + (reasoning === null ? 0 : reasoning); if (!Number.isSafeInteger(otelOutput)) usageFail("invalid_count");
    const otelAttributes = { "gen_ai.operation.name": "generate_content", "gen_ai.provider.name": "gcp.gemini", "gen_ai.request.model": requestModel, "gen_ai.request.stream": true, "gen_ai.output.type": "speech", "gen_ai.usage.input_tokens": input, "gen_ai.usage.output_tokens": otelOutput, "server.address": "generativelanguage.googleapis.com", "server.port": 443 };
    if (cached !== null) otelAttributes["gen_ai.usage.cache_read.input_tokens"] = cached;
    if (reasoning !== null) otelAttributes["gen_ai.usage.reasoning.output_tokens"] = reasoning;
    return { schema_version: 1, provider: "gcp.gemini", provider_request_id: null, local_correlation_id: `live-session:${session}`, usage_sequence: context.usage_sequence, occurred_at: new Date(context.occurred_at).toISOString(), owner_id: owner, financial_unit_id: "life_manager_saas", trace_id: context.trace_id, request_model: requestModel, response_model: null, tokens: { input, output, cached_input: cached, reasoning_output: reasoning, tool_input: tool, total }, evidence_status: "provider_reported", otel_attributes: otelAttributes };
  } catch (error) {
    if (usageInternal(error)) throw error;
    usageFail("invalid_input");
  }
}

function normalizeLocalAgentUsageEvent(input, mapping) {
  try {
    if (!plainLocalAgentUsageInput(input) || !plainLocalAgentUsageInput(mapping) || !plainLocalAgentUsageInput(input.tokens)) localAgentUsageFail("invalid_input");
    const sourceRowRef = mapping.source_row_ref;
    if (!Object.prototype.hasOwnProperty.call(mapping, "source_row_ref") || typeof sourceRowRef !== "string" || !/^(?!0{64})[0-9a-f]{64}$/.test(sourceRowRef)) localAgentUsageFail("invalid_source_row_ref");
    if (input.version !== 1) localAgentUsageFail("invalid_version");
    if (typeof input.event_id !== "string" || !/^[0-9a-f]{24}$/.test(input.event_id)) localAgentUsageFail("invalid_event_id");
    if (!validLocalAgentUsageTimestamp(input.timestamp)) localAgentUsageFail("invalid_timestamp");
    for (const field of ["loop", "task_label", "provider", "provider_name", "model"]) {
      if (typeof input[field] !== "string" || input[field].length === 0 || input[field].trim() !== input[field]) localAgentUsageFail(`invalid_${field}`);
    }
    if (input.upstream_model !== null && (typeof input.upstream_model !== "string" || input.upstream_model.length === 0 || input.upstream_model.trim() !== input.upstream_model)) localAgentUsageFail("invalid_upstream_model");
    if (!Number.isSafeInteger(input.attempt) || input.attempt < 1) localAgentUsageFail("invalid_attempt");
    if (input.status !== "success" && input.status !== "failed") localAgentUsageFail("invalid_status");
    if (input.measurement !== "provider_reported" && input.measurement !== "unavailable") localAgentUsageFail("invalid_measurement");
    const tokens = input.tokens;
    const tokenFields = ["input", "cached_input", "cache_creation_input", "output", "reasoning_output", "total"];
    for (const field of tokenFields) {
      if (input.measurement === "provider_reported") {
        if (!Number.isSafeInteger(tokens[field]) || tokens[field] < 0) localAgentUsageFail("invalid_count");
      } else if (tokens[field] !== null) localAgentUsageFail("invalid_count");
    }
    const financialUnitId = Object.prototype.hasOwnProperty.call(mapping, "financial_unit_id") ? mapping.financial_unit_id : null;
    if (financialUnitId !== null && (typeof financialUnitId !== "string" || financialUnitId.length === 0 || financialUnitId.trim() !== financialUnitId)) localAgentUsageFail("invalid_financial_unit");
    const attributed = financialUnitId !== null;
    const normalized = {
      schema_version: 1,
      source_ledger: "local_agent_usage",
      source_event_id: `local_agent_usage:${sourceRowRef}`,
      runner_event_id: input.event_id,
      occurred_at: new Date(input.timestamp).toISOString(),
      provider: input.provider,
      provider_name: input.provider_name,
      request_model: input.model,
      upstream_model: input.upstream_model,
      run: { loop: input.loop, task_label: input.task_label, attempt: input.attempt, status: input.status },
      financial_unit_id: financialUnitId,
      attribution_status: attributed ? "attributed" : "unattributed",
      measurement: input.measurement,
      token_value_basis: input.measurement === "provider_reported" ? "runner_normalized_provider_usage" : "unavailable",
      tokens: Object.fromEntries(tokenFields.map((field) => [field, tokens[field]])),
      coverage_status: input.measurement === "provider_reported" ? "covered" : "missing_usage",
    };
    return freezeLocalAgentUsage(normalized);
  } catch (error) {
    if (localAgentUsageInternal(error)) throw error;
    localAgentUsageFail("invalid_input");
  }
}

function reduceLocalAgentUsageEvents(pairs) {
  try {
    if (!Array.isArray(pairs)) localAgentUsageFail("invalid_input");
    const groups = new Map();
    for (let index = 0; index < pairs.length; index += 1) {
      if (!Object.prototype.hasOwnProperty.call(pairs, index)) localAgentUsageFail("invalid_input");
      const pair = pairs[index]; exactLocalAgentUsage(pair, LOCAL_AGENT_PAIR_KEYS);
      const event = normalizeLocalAgentUsageEvent(pair.input, pair.context), canonical = canonicalJson(event), id = event.source_event_id;
      const group = groups.get(id) || { rows: [], variants: new Map() };
      group.rows.push(event); group.variants.set(canonical, event); groups.set(id, group);
    }
    const accepted = [], counts = { accepted_rows: 0, duplicate_rows: 0, conflicting_rows: 0 };
    for (const group of groups.values()) {
      if (group.variants.size > 1) counts.conflicting_rows += group.rows.length;
      else { counts.accepted_rows += 1; counts.duplicate_rows += group.rows.length - 1; accepted.push(group.variants.values().next().value); }
    }
    accepted.sort((a, b) => a.source_event_id < b.source_event_id ? -1 : a.source_event_id > b.source_event_id ? 1 : 0);
    const events = accepted.map((event) => JSON.parse(canonicalJson(event))), runnerSets = new Map();
    for (const event of accepted) { const ids = runnerSets.get(event.runner_event_id) || new Set(); ids.add(event.source_event_id); runnerSets.set(event.runner_event_id, ids); }
    const missing = accepted.filter((event) => event.measurement === "unavailable").length;
    const collisions = [...runnerSets.values()].filter((ids) => ids.size > 1).length;
    const coverage_exceptions = []; if (counts.conflicting_rows) coverage_exceptions.push("conflicting_usage"); if (missing) coverage_exceptions.push("missing_usage"); if (collisions) coverage_exceptions.push("runner_identity_collision");
    return freezeLocalAgentUsage({ events, discovered_rows: pairs.length, ...counts, missing_usage_rows: missing, runner_collision_groups: collisions, coverage_exceptions });
  } catch (error) {
    if (localAgentUsageInternal(error)) throw error;
    localAgentUsageFail("invalid_input");
  }
}

function finite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function rounded(value) {
  return Number(value.toFixed(12));
}

// Pure rows -> JSON summary. `rows` and `nowMs` are injected; no DB, clock, or mutation occurs here.
function businessSummary(daysBack, rows, nowMs) {
  const days = Math.max(0, finite(daysBack));
  const now = finite(nowMs);
  const since = now - days * 86400000;
  const summary = { calls: 0, call_minutes: 0, est_cost_usd: 0, per_uid: {} };
  for (const row of Array.isArray(rows) ? rows : []) {
    const ts = Date.parse(row && row.ts);
    if (!Number.isFinite(ts) || ts < since || ts > now) continue;
    const uid = row.uid == null || row.uid === "" ? "unknown" : String(row.uid);
    const item = summary.per_uid[uid] || { calls: 0, call_minutes: 0, est_cost_usd: 0 };
    if (row.kind === "telnyx_call") {
      summary.calls += 1;
      item.calls += 1;
      summary.call_minutes += finite(row.quantity) / 60;
      item.call_minutes += finite(row.quantity) / 60;
    }
    summary.est_cost_usd += finite(row.est_usd);
    item.est_cost_usd += finite(row.est_usd);
    summary.per_uid[uid] = item;
  }
  summary.call_minutes = rounded(summary.call_minutes);
  summary.est_cost_usd = rounded(summary.est_cost_usd);
  for (const item of Object.values(summary.per_uid)) {
    item.call_minutes = rounded(item.call_minutes);
    item.est_cost_usd = rounded(item.est_cost_usd);
  }
  return summary;
}

module.exports = { recordCost, recordDailyComposioPoll, monthlyComposioCallCount, normalizeApiCostEvent, normalizeGeminiUsageEvidence, normalizeGeminiLiveUsageEvidence, normalizeLocalAgentUsageEvent, reduceLocalAgentUsageEvents, businessSummary };
