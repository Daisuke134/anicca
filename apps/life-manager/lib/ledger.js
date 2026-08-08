"use strict";

function headers(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

// `actualStatus` answers only whether a provider invoice/measurement exists.
// The way a number was obtained lives in `costClassification` so an estimate
// can never masquerade as a known billed amount.
const ACTUAL_STATUS = new Set(["known", "unknown"]);
const COST_CLASSIFICATION = new Set(["measured", "estimated", "fixed", "unknown"]);

function nonEmpty(value, field) {
  const text = value == null ? "" : String(value).trim();
  if (!text) throw new Error(`${field} is required`);
  return text;
}

function nonNegative(value, field, { nullable = false } = {}) {
  if (value == null && nullable) return null;
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${field} must be a non-negative number or null`);
  return number;
}

function validateProviderCostEvent(input = {}) {
  const provider = nonEmpty(input.provider, "provider");
  const sku = nonEmpty(input.sku, "sku");
  const operation = nonEmpty(input.operation, "operation");
  const requestId = nonEmpty(input.requestId, "requestId");
  const unit = nonEmpty(input.unit, "unit");
  const pricingVersion = nonEmpty(input.pricingVersion, "pricingVersion");
  const quantity = nonNegative(input.quantity, "quantity");
  const estimatedUsd = nonNegative(input.estimatedUsd, "estimatedUsd", { nullable: true });
  const actualBilledUsd = nonNegative(input.actualBilledUsd, "actualBilledUsd", { nullable: true });
  const actualStatus = input.actualStatus == null
    ? (actualBilledUsd == null ? "unknown" : "known")
    : String(input.actualStatus);
  if (!ACTUAL_STATUS.has(actualStatus)) throw new Error(`actualStatus must be one of ${Array.from(ACTUAL_STATUS).join(", ")}`);
  if (actualStatus === "known" && actualBilledUsd == null) throw new Error("known billing requires actualBilledUsd");
  if (actualStatus === "unknown" && actualBilledUsd != null) throw new Error("unknown billing must keep actualBilledUsd null");
  const costClassification = input.costClassification == null
    ? (actualBilledUsd != null ? "measured" : estimatedUsd != null ? "estimated" : "unknown")
    : String(input.costClassification);
  if (!COST_CLASSIFICATION.has(costClassification)) {
    throw new Error(`costClassification must be one of ${Array.from(COST_CLASSIFICATION).join(", ")}`);
  }
  if (costClassification === "measured" && actualBilledUsd == null) throw new Error("measured classification requires actualBilledUsd");
  if (costClassification === "estimated" && estimatedUsd == null) throw new Error("estimated classification requires estimatedUsd");
  if (costClassification === "fixed" && actualBilledUsd == null && estimatedUsd == null) {
    throw new Error("fixed classification requires actualBilledUsd or estimatedUsd");
  }
  if (actualStatus === "known" && !["measured", "fixed"].includes(costClassification)) {
    throw new Error("known billing must use measured or fixed classification");
  }
  const metadata = input.metadata == null ? {} : input.metadata;
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) throw new Error("metadata must be an object");
  return {
    uid: input.uid == null ? null : String(input.uid),
    provider, sku, operation, requestId, quantity, unit, pricingVersion,
    estimatedUsd, actualBilledUsd, actualStatus, costClassification,
    metadata,
  };
}

function failureShape(event, error) {
  return {
    kind: "provider_cost_ledger_write_failed",
    provider: event.provider,
    sku: event.sku,
    operation: event.operation,
    requestId: event.requestId,
    uid: event.uid,
    quantity: event.quantity,
    unit: event.unit,
    error: {
      message: error && error.message ? String(error.message) : String(error),
      status: error && Number.isFinite(Number(error.status)) ? Number(error.status) : null,
    },
    failedAt: new Date().toISOString(),
  };
}

async function emitProviderCostFailure(event, error, opts = {}) {
  const failure = failureShape(event, error);
  const log = opts.log || console.error;
  try { log("[ledger] provider cost write failed", JSON.stringify(failure)); } catch { /* logging is best effort */ }
  if (opts.outboxStore && typeof opts.outboxStore.insert === "function") {
    try { await opts.outboxStore.insert(failure); } catch (outboxError) {
      try { log("[ledger] provider cost failure outbox failed", outboxError && outboxError.message ? outboxError.message : outboxError); } catch { /* noop */ }
    }
  } else if (opts.failureOutboxUrl && opts.fetchImpl && typeof opts.fetchImpl === "function") {
    try {
      await opts.fetchImpl(opts.failureOutboxUrl, {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, opts.failureOutboxHeaders || {}),
        body: JSON.stringify(failure),
      });
    } catch { /* owner alert below remains the visible signal */ }
  }
  if (typeof opts.ownerAlert === "function") {
    try { await opts.ownerAlert(failure); } catch (alertError) {
      try { log("[ledger] provider cost owner alert failed", alertError && alertError.message ? alertError.message : alertError); } catch { /* noop */ }
    }
  }
  return failure;
}

// Complete provider cost event. Unlike the legacy recordCost wrapper below,
// this function never fills an absent actual amount with zero.
async function recordProviderCost(input = {}, opts = {}) {
  let event;
  try {
    event = validateProviderCostEvent(input);
  } catch (error) {
    const invalidEvent = {
      provider: input.provider == null ? "unknown" : String(input.provider),
      sku: input.sku == null ? "unknown" : String(input.sku),
      operation: input.operation == null ? "unknown" : String(input.operation),
      requestId: input.requestId == null ? "unknown" : String(input.requestId),
      uid: input.uid == null ? null : String(input.uid),
      quantity: null,
      unit: input.unit == null ? "unknown" : String(input.unit),
    };
    await emitProviderCostFailure(invalidEvent, error, opts);
    return false;
  }
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || typeof fetchImpl !== "function") {
    await emitProviderCostFailure(event, new Error("Supabase credentials or fetch implementation missing"), opts);
    return false;
  }
  const body = {
    uid: event.uid,
    provider: event.provider,
    sku: event.sku,
    operation: event.operation,
    request_id: event.requestId,
    quantity: event.quantity,
    unit: event.unit,
    pricing_version: event.pricingVersion,
    estimated_usd: event.estimatedUsd,
    // Keep the old reader column populated in the same insert while the
    // additive migration rolls through mixed deployments.
    est_usd: event.estimatedUsd,
    actual_billed_usd: event.actualBilledUsd,
    actual_status: event.actualStatus,
    cost_classification: event.costClassification,
    metadata: event.metadata,
  };
  // Existing daily/financial readers still understand the legacy kind/meta pair. Emit it only for
  // explicitly migrated compatibility events; the provider contract itself remains complete above.
  if (input.legacyKind != null) body.kind = String(input.legacyKind);
  if (input.legacyMeta != null) body.meta = input.legacyMeta;
  try {
    const response = await fetchImpl(`${supaUrl.replace(/\/$/u, "")}/rest/v1/lm_api_cost`, {
      method: "POST",
      headers: headers(supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
      body: JSON.stringify(body),
    });
    if (!response || !response.ok) {
      const error = new Error(`Supabase provider cost insert failed (${response && response.status})`);
      error.status = response && response.status;
      throw error;
    }
    if (event.provider === "telnyx" && event.actualStatus === "known" && event.actualBilledUsd != null && event.operation === "call_cdr") {
      try {
        const { settleProviderVoice } = require("./provider-budget.js");
        const settled = await settleProviderVoice({
          uid: event.uid,
          requestId: event.requestId,
          actualBilledUsd: event.actualBilledUsd,
          reservationRequestId: event.metadata && event.metadata.reservationRequestId,
        }, opts);
        if (!settled) (opts.log || console.error)("[ledger] voice settlement failed", event.requestId);
      } catch (settlementError) {
        try { (opts.log || console.error)("[ledger] voice settlement failed", settlementError && settlementError.message); } catch { /* best effort */ }
      }
    }
    return true;
  } catch (error) {
    await emitProviderCostFailure(event, error, opts);
    return false;
  }
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
    // The migrated daily row carries legacy kind explicitly, so the existing indexed query remains
    // the single duplicate guard while provider dimensions are added to the same insert.
    return recordProviderCost({
      uid, provider: "composio", sku: "calendar_poll", operation: "daily_poll",
      requestId: `composio:daily_poll:${uid}:${dayStart.toISOString().slice(0, 10)}`,
      quantity: 1, unit: "day", pricingVersion: "composio-2026-08",
      estimatedUsd: null, actualBilledUsd: null, actualStatus: "unknown", costClassification: "unknown",
      metadata: { day: dayStart.toISOString().slice(0, 10) },
      legacyKind: "composio_poll", legacyMeta: { day: dayStart.toISOString().slice(0, 10) },
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
    const legacyCount = match ? Number(match[1]) : 0;
    if (legacyCount > 0) return legacyCount;
    // New provider rows use provider/operation dimensions. Keep the legacy query first so mixed
    // deployments and existing budget dashboards continue to work without a migration race.
    const providerQuery = ["select=id", "provider=eq.composio", "operation=eq.tool_execute",
      `ts=gte.${encodeURIComponent(monthStart.toISOString())}`,
      `ts=lt.${encodeURIComponent(nextMonth.toISOString())}`, "limit=1"].join("&");
    const providerResponse = await fetchImpl(`${supaUrl}/rest/v1/lm_api_cost?${providerQuery}`, {
      headers: headers(supaKey, { Prefer: "count=exact" }),
    });
    if (!providerResponse.ok) throw new Error(`Supabase provider monthly count failed (${providerResponse.status})`);
    const providerRange = providerResponse.headers && providerResponse.headers.get("content-range");
    const providerMatch = String(providerRange || "").match(/\/(\d+)$/);
    return providerMatch ? Number(providerMatch[1]) : 0;
  } catch (error) {
    log("[ledger] monthly Composio count failed", error && error.message ? error.message : error);
    return null;
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

module.exports = {
  ACTUAL_STATUS,
  COST_CLASSIFICATION,
  recordCost,
  recordProviderCost,
  validateProviderCostEvent,
  recordDailyComposioPoll,
  monthlyComposioCallCount,
  businessSummary,
};
