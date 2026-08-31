"use strict";

const { EXCLUDED_KINDS, normaliseEntry, usdMicrosForEntry } = require("./earnings-ledger.js");

const COLUMNS = { found: new Set(["DISCOVERED", "QUALIFYING", "QUALIFIED", "CLAIMED"]), working: new Set(["WORKING", "READY_FOR_EFFECT", "QA_ACCEPTED"]), needs_you: new Set(["NEEDS_HUMAN"]), waiting: new Set(["EFFECT_UNCERTAIN", "SUBMITTED", "WON", "CONTRACTED", "PAYMENT_PENDING"]), done: new Set(["INELIGIBLE", "EXPIRED", "LOST", "DELIVERED"]), paid: new Set(["PAID_SETTLED", "REVENUE_RECORDED"]) };
const NAMES = Object.freeze(Object.keys(COLUMNS));
const MONEY = /^\d+$/;
const ACTIVE_JOB_STATUSES = new Set(["running", "waiting_agent", "reconciling"]);

function fail(message) { throw new Error(message); }

function rows(value, tenantId, label, required = true) {
  if (value == null) return Object.freeze([]);
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return Object.freeze(value.map((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row) || (required && row.tenant_id !== tenantId) || (row.tenant_id != null && row.tenant_id !== tenantId)) fail("money printer tenant mismatch");
    return Object.freeze({ ...row });
  }));
}

function money(value, label, optional = false) {
  if (value == null && optional) return "0";
  const raw = typeof value === "bigint" ? value.toString() : String(value == null ? "" : value).trim();
  if (!MONEY.test(raw)) fail(`${label} must be an exact non-negative integer`);
  return BigInt(raw).toString();
}

function currency(value, label) {
  const code = typeof value === "string" ? value : "";
  if (!/^[A-Z]{3}$/.test(code)) fail(`${label} currency invalid`);
  return code;
}

function addMoney(total, code, amount) {
  total[code] = (BigInt(total[code] || "0") + BigInt(amount)).toString();
}

function moneyMap(total) {
  return Object.freeze(Object.fromEntries(Object.keys(total).sort().map((code) => [code, total[code]])));
}

function ref(value, prefix, tenantId, label) {
  const raw = String(value == null ? "" : value).trim();
  if (!raw || /\s/.test(raw) || raw.length > 1024) fail(`${label} reference invalid`);
  if (raw.includes("://")) {
    if (raw.startsWith(`${prefix}://`) && !raw.startsWith(`${prefix}://${encodeURIComponent(tenantId)}/`)) fail("money printer tenant mismatch");
    return raw;
  }
  return `${prefix}://${encodeURIComponent(tenantId)}/${encodeURIComponent(raw)}`;
}

function link(value, label) {
  if (value == null || value === "") return null;
  let parsed;
  try { parsed = new URL(String(value).trim()); } catch { fail(`${label} must be an HTTPS URL`); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password) fail(`${label} must be an HTTPS URL`);
  return String(value).trim();
}

function observed(row, fallback) {
  const ms = Date.parse(String(row.observed_at || row.occurred_at || row.updated_at || row.created_at || ""));
  return Number.isFinite(ms) ? new Date(ms).toISOString() : fallback;
}

function projectMoneyPrinter(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) fail("money printer scope invalid");
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  const ms = Date.parse(String(input.observedAt == null ? "" : input.observedAt));
  if (!tenantId || !Number.isFinite(ms)) fail("money printer scope invalid");
  const observedAt = new Date(ms).toISOString();
  const data = {
    opportunities: rows(input.opportunities, tenantId, "opportunities"), runtimeJobs: rows(input.runtimeJobs, tenantId, "runtime jobs"),
    generalReceipts: rows(input.generalReceipts, tenantId, "general receipts", false), applicationReceipts: rows(input.applicationReceipts, tenantId, "application receipts", false),
    humanTasks: rows(input.humanTasks, tenantId, "human tasks"), earnings: rows(input.earnings, tenantId, "earnings"),
  };
  const columns = Object.fromEntries(NAMES.map((name) => [name, []]));
  const activity = [];
  const opportunityValue = {}; const paid = {};
  let running = 0; let working = 0;
  const openTasksByJob = new Map();
  const opportunitiesById = new Map();
  const activeJobs = new Set();
  for (const row of data.opportunities) {
    const opportunityId = String(row.opportunity_id == null ? "" : row.opportunity_id).trim();
    if (opportunityId) {
      if (opportunitiesById.has(opportunityId)) fail("money printer human task opportunity relation invalid");
      opportunitiesById.set(opportunityId, row);
    }
  }
  for (const row of data.runtimeJobs) {
    const status = String(row.status || "").trim().toLowerCase();
    const jobId = typeof row.job_id === "string" ? row.job_id.trim() : "";
    if (ACTIVE_JOB_STATUSES.has(status) && /^goal:[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(jobId)
      && opportunitiesById.has(jobId.slice(5))) activeJobs.add(jobId);
  }
  for (const row of data.humanTasks) {
    const status = String(row.status || "").trim().toLowerCase();
    if (!status) fail("money printer human task status invalid");
    const rawJobId = row.job_id;
    const jobId = typeof rawJobId === "string" ? rawJobId.trim() : "";
    if (rawJobId !== jobId || !/^goal:[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(jobId)
      || !opportunitiesById.has(jobId.slice(5))) {
      fail("money printer human task opportunity relation invalid");
    }
    if (["open", "waiting_for_human", "needs_you", "pending"].includes(status)) {
      if (openTasksByJob.has(jobId)) {
        fail("money printer human task opportunity relation invalid");
      }
      openTasksByJob.set(jobId, row);
    }
  }

  for (const row of data.opportunities) {
    const status = String(row.status == null ? row.state || "" : row.status).trim().toUpperCase();
    const column = NAMES.find((name) => COLUMNS[name].has(status));
    if (!column) fail("money printer opportunity state invalid");
    const rawValue = row.value_minor ?? row.reward_minor ?? row.amount_minor ?? row.budget_max_minor;
    const valueMinor = money(rawValue, "opportunity value", true);
    const code = rawValue == null ? null : currency(row.currency, "opportunity");
    const card = Object.freeze({ opportunity_ref: ref(row.opportunity_ref || row.opportunity_id || row.external_id || row.id, "opportunity", tenantId, "opportunity"), title: String(row.title || "Opportunity").trim() || "Opportunity", status, value_minor: valueMinor, currency: code, source_url: link(row.source_url ?? row.url, "opportunity source") });
    const jobId = `goal:${String(row.opportunity_id == null ? "" : row.opportunity_id).trim()}`;
    const ownerTask = openTasksByJob.get(jobId);
    columns[ownerTask ? "needs_you" : activeJobs.has(jobId) ? "working" : column].push(card);
    if (code) addMoney(opportunityValue, code, valueMinor);
    if (["WORKING", "READY_FOR_EFFECT", "QA_ACCEPTED"].includes(status)) working += 1;
    activity.push(Object.freeze({ kind: "opportunity", ref: card.opportunity_ref, status, observed_at: observed(row, observedAt) }));
  }
  for (const row of data.runtimeJobs) {
    const status = String(row.status || "").trim().toLowerCase();
    if (ACTIVE_JOB_STATUSES.has(status)) running += 1;
    activity.push(Object.freeze({ kind: "work", ref: ref(row.job_ref || row.job_id || row.id, "runtime-job", tenantId, "runtime job"), status, observed_at: observed(row, observedAt) }));
  }
  for (const row of data.humanTasks) {
    const status = String(row.status || "").trim().toLowerCase();
    activity.push(Object.freeze({
      kind: "human_task", ref: ref(row.task_ref || row.task_id || row.id, "human-task", tenantId, "human task"),
      job_ref: ref(row.job_id, "runtime-job", tenantId, "human task job"), status, observed_at: observed(row, observedAt),
    }));
  }
  for (const [kind, receiptRows] of [["work_receipt", data.generalReceipts], ["application_receipt", data.applicationReceipts]]) {
    for (const row of receiptRows) {
      const id = row.receipt_ref || row.receipt_id || row.external_receipt_ref || row.application_external_id || row.id || row.job_id;
      const receiptUrl = link(row.receipt_url || row.url || row.link, "receipt link");
      if (id) activity.push(Object.freeze({ kind, ref: ref(id, "receipt", tenantId, `${kind} receipt`), status: String(row.status || "observed").trim().toLowerCase(), observed_at: observed(row, observedAt), ...(receiptUrl ? { receipt_url: receiptUrl } : {}) }));
    }
  }
  for (const row of data.earnings) {
    if (row.verified !== true) fail("money printer earnings must be verified exact money");
    const code = currency(row.currency, "earning");
    const amount = money(row.amount_minor, "earning amount");
    let canonicalAmount = amount;
    if (row.wallet_address != null && row.kind != null && row.currency != null && row.occurred_at != null) canonicalAmount = (usdMicrosForEntry(normaliseEntry({ ...row, amount_minor: amount })) / 10000n).toString();
    if (!EXCLUDED_KINDS.has(row.kind) && (!row.kind || row.kind === "financial_external_income")) addMoney(paid, code, canonicalAmount);
    const receiptUrl = link(row.receipt_url || row.receiptUrl || row.url, "earning receipt link");
    activity.push(Object.freeze({ kind: "earning", ref: ref(row.entry_ref || row.entry_key || row.id, "earning", tenantId, "earning"), status: "verified", amount_minor: canonicalAmount, observed_at: observed(row, observedAt), ...(receiptUrl ? { receipt_url: receiptUrl } : {}) }));
  }
  return Object.freeze({ observed_at: observedAt, metrics: Object.freeze({ agents_working: running || working, needs_you: columns.needs_you.length, opportunity_value: moneyMap(opportunityValue), paid_verified: moneyMap(paid) }), columns: Object.freeze(Object.fromEntries(NAMES.map((name) => [name, Object.freeze(columns[name])]))), activity: Object.freeze(activity) });
}

module.exports = { projectMoneyPrinter };
