"use strict";

const { createHash } = require("node:crypto");
const { isIP } = require("node:net");

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const HASH = /^[0-9a-f]{64}$/;
const CURRENCY = /^[A-Z]{3}$/;
const STATUS = "DISCOVERED";
const OPPORTUNITY_STATUSES = new Set([
  "DISCOVERED", "QUALIFYING", "QUALIFIED", "CLAIMED", "WORKING",
  "READY_FOR_EFFECT", "QA_ACCEPTED", "NEEDS_HUMAN", "EFFECT_UNCERTAIN",
  "SUBMITTED", "WON", "CONTRACTED", "PAYMENT_PENDING", "INELIGIBLE",
  "EXPIRED", "LOST", "DELIVERED", "PAID_SETTLED", "REVENUE_RECORDED",
]);
const LOOP_ID = "life-manager.manager";
const CAPABILITY = "general-agent.work";

function invalid(label) {
  throw new Error(`money printer opportunity ${label} invalid`);
}

function text(value, label, pattern, max) {
  if (typeof value !== "string") invalid(label);
  const result = value.trim();
  if (!result || result.length > max || (pattern && !pattern.test(result))) invalid(label);
  return result;
}

function canonicalUrl(value) {
  const raw = text(value, "source URL", null, 4_096);
  let url;
  try { url = new URL(raw); } catch { invalid("source URL"); }
  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || !url.hostname
    || url.hostname === "localhost"
    || isIP(url.hostname)
  ) invalid("source URL");
  url.hash = "";
  return url.toString();
}

function exactMinor(value) {
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || value < 0) invalid("value");
    return String(value);
  }
  const raw = typeof value === "bigint" ? value.toString() : String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw)) invalid("value");
  return BigInt(raw).toString();
}

function observedAt(value) {
  const raw = text(value, "observed time", null, 100);
  if (!/[zZ]|[+-]\d\d:\d\d$/.test(raw)) invalid("observed time");
  const milliseconds = Date.parse(raw);
  if (!Number.isFinite(milliseconds)) invalid("observed time");
  return new Date(milliseconds).toISOString();
}

function canonicalOpportunityInput(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid("input");
  const uid = text(input.tenantId, "tenant", TENANT_ID, 200);
  const sourceUrl = canonicalUrl(input.sourceUrl);
  const opportunityId = createHash("sha256")
    .update(`${uid}\n${sourceUrl}`, "utf8")
    .digest("hex");
  return Object.freeze({
    uid,
    opportunity_id: opportunityId,
    source_url: sourceUrl,
    title: text(input.title, "title", null, 300),
    goal_statement: text(input.goalStatement, "goal statement", null, 4_000),
    value_minor: exactMinor(input.valueMinor),
    currency: text(String(input.currency == null ? "" : input.currency).toUpperCase(), "currency", CURRENCY, 3),
    status: STATUS,
    goal_ref: `intent-entry://${encodeURIComponent(uid)}/${opportunityId}`,
    job_id: `goal:${opportunityId}`,
    observed_at: observedAt(input.observedAt),
  });
}

function buildOpportunity(input = {}) {
  return canonicalOpportunityInput(input);
}

function readbackRow(result) {
  if (result && result.row && typeof result.row === "object") return result.row;
  if (result && result.opportunity && typeof result.opportunity === "object") return result.opportunity;
  return result;
}

function assertReadback(result, expected) {
  const row = readbackRow(result);
  if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error("money printer opportunity readback invalid");
  const actualUid = row.uid == null ? row.tenant_id : row.uid;
  const fields = [
    [actualUid, expected.uid],
    [row.opportunity_id, expected.opportunity_id],
    [row.source_url, expected.source_url],
    [row.title, expected.title],
    [row.goal_statement, expected.goal_statement],
    [row.value_minor == null ? null : String(row.value_minor), expected.value_minor],
    [row.currency, expected.currency],
    [row.goal_ref, expected.goal_ref],
  ];
  if (fields.some(([actual, wanted]) => actual !== wanted)) {
    throw new Error("money printer opportunity readback mismatch");
  }
  if (!OPPORTUNITY_STATUSES.has(String(row.status || "").toUpperCase())) {
    throw new Error("money printer opportunity readback mismatch");
  }
  if (row.observed_at == null || observedAt(String(row.observed_at)) !== expected.observed_at) {
    throw new Error("money printer opportunity readback mismatch");
  }
  if (row.job_id != null && row.job_id !== expected.job_id) {
    throw new Error("money printer opportunity readback mismatch");
  }
  return Object.freeze({ ...row, job_id: row.job_id || expected.job_id });
}

function storeMethod(store) {
  for (const name of ["createOpportunity", "createAtomic", "create"]) {
    if (store && typeof store[name] === "function") return store[name].bind(store);
  }
  throw new Error("money printer opportunity store unavailable");
}

async function createOpportunity(input, store) {
  const expected = canonicalOpportunityInput(input);
  const target = store || createSupabaseOpportunityStore();
  return assertReadback(await storeMethod(target)(expected), expected);
}

function credentials(options = {}) {
  const supaUrl = String(options.supaUrl || process.env.SUPABASE_URL || "").replace(/\/$/, "");
  const supaKey = options.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || typeof fetchImpl !== "function") {
    throw new Error("money printer opportunity store unavailable");
  }
  return { supaUrl, supaKey, fetchImpl };
}

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
}

function createSupabaseOpportunityStore(options = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(options);
  async function create(opportunity) {
    const response = await fetchImpl(`${supaUrl}/rest/v1/rpc/create_lm_money_opportunity`, {
      method: "POST",
      headers: headers(supaKey),
      body: JSON.stringify({
        p_uid: opportunity.uid,
        p_opportunity_id: opportunity.opportunity_id,
        p_source_url: opportunity.source_url,
        p_title: opportunity.title,
        p_goal_statement: opportunity.goal_statement,
        p_value_minor: opportunity.value_minor,
        p_currency: opportunity.currency,
        p_observed_at: opportunity.observed_at,
        p_goal_ref: opportunity.goal_ref,
      }),
    });
    if (!response || !response.ok) {
      throw new Error(`money printer opportunity RPC failed (${response ? response.status : "no response"})`);
    }
    const body = await response.json();
    const rows = Array.isArray(body) ? body : body && typeof body === "object" ? [body] : [];
    if (rows.length !== 1) throw new Error("money printer opportunity RPC returned no row");
    return rows[0];
  }
  return Object.freeze({ createOpportunity: create, createAtomic: create, create });
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  STATUS,
  buildOpportunity,
  canonicalOpportunityInput,
  createOpportunity,
  createSupabaseOpportunityStore,
  opportunityIdFor(input) { return canonicalOpportunityInput(input).opportunity_id; },
};
