"use strict";

const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { fail: costEventFail, plain: plainCostRow, timestamp: validCostTimestamp } = createCfoSupabaseRpc("cfo_business_ledger_invalid:");

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

module.exports = { recordCost, recordDailyComposioPoll, monthlyComposioCallCount, normalizeApiCostEvent, businessSummary };
