"use strict";

const { isIP } = require("node:net");
const { createMoneyPrinterRuntimeStore } = require("./money-printer-runtime-store.js");

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const MACHINE_ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/;
const OPPORTUNITY_JOB_ID = /^goal:[0-9a-f]{64}$/;
const HASH = /^[0-9a-f]{64}$/;
const MONEY = /^\d+$/;
const CURRENCY = /^[A-Z]{3}$/;
const APPLICATION_RECEIPT_KINDS = new Set([
  "application",
  "application_receipt",
  "marketplace_application",
  "outbound_event_application",
]);

function invalid(label) {
  throw new Error(`money printer source ${label} invalid`);
}

function credentials(options = {}) {
  const supaUrl = String(options.supaUrl || process.env.SUPABASE_URL || "").replace(/\/$/, "");
  const supaKey = options.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || typeof fetchImpl !== "function") {
    throw new Error("money printer source unavailable");
  }
  return { supaUrl, supaKey, fetchImpl };
}

function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function tenantFromScope(scope) {
  if (!scope || typeof scope !== "object" || Array.isArray(scope)) invalid("scope");
  const uid = String(scope.uid == null ? "" : scope.uid).trim();
  if (!TENANT_ID.test(uid)) invalid("scope");
  if (scope.tenantId != null && String(scope.tenantId).trim() !== uid) invalid("scope");
  return uid;
}

function tableUrl(base, table, params) {
  const url = new URL(`${base}/rest/v1/${table}`);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.toString();
}

async function readRows(fetchImpl, url, key, label) {
  let response;
  try {
    response = await fetchImpl(url, { headers: headers(key) });
  } catch (error) {
    throw new Error(`money printer source ${label} read failed: ${error && error.message ? error.message : error}`);
  }
  if (!response || !response.ok) {
    throw new Error(`money printer source ${label} read failed (${response ? response.status : "no response"})`);
  }
  let body;
  try { body = await response.json(); } catch { throw new Error(`money printer source ${label} returned invalid JSON`); }
  if (!Array.isArray(body)) throw new Error(`money printer source ${label} returned a non-array body`);
  return body;
}

function tenantValue(row, uid, key = "tenant_id") {
  const value = row && row[key];
  if (String(value == null ? "" : value) !== uid) invalid("tenant row");
  return uid;
}

function requiredText(value, label, max = 4_096) {
  if (typeof value !== "string" || !value.trim() || value.length > max) invalid(label);
  return value;
}

function requiredMoney(value, label) {
  const raw = String(value == null ? "" : value).trim();
  if (!MONEY.test(raw)) invalid(label);
  return BigInt(raw).toString();
}

function requiredTime(value, label) {
  const raw = String(value == null ? "" : value).trim();
  if (!raw || !Number.isFinite(Date.parse(raw))) invalid(label);
  return new Date(Date.parse(raw)).toISOString();
}

function safeApplicationId(value) {
  const raw = String(value == null ? "" : value).trim();
  return /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/.test(raw) ? raw : null;
}

function publicUrl(value) {
  if (value == null) invalid("public URL");
  let url;
  try { url = new URL(String(value).trim()); } catch { invalid("public URL"); }
  if (url.protocol !== "https:" || url.username || url.password || url.hostname === "localhost" || isIP(url.hostname)) invalid("public URL");
  return url.toString();
}

function mapOpportunity(row, uid) {
  tenantValue(row, uid, "uid");
  if (!HASH.test(String(row.opportunity_id || ""))) invalid("opportunity id");
  if (!CURRENCY.test(String(row.currency || ""))) invalid("opportunity currency");
  return {
    tenant_id: uid,
    opportunity_id: requiredText(row.opportunity_id, "opportunity id", 64),
    source_url: publicUrl(row.source_url),
    title: requiredText(row.title, "opportunity title", 300),
    value_minor: requiredMoney(row.value_minor, "opportunity value"),
    currency: requiredText(row.currency, "opportunity currency", 3),
    status: requiredText(row.status, "opportunity status", 64),
    goal_ref: requiredText(row.goal_ref, "opportunity goal ref", 1_024),
    observed_at: requiredTime(row.observed_at, "opportunity observed time"),
  };
}

function mapRuntimeJob(row, uid) {
  tenantValue(row, uid);
  return {
    tenant_id: uid,
    job_id: requiredText(row.job_id, "runtime job id", 200),
    status: requiredText(row.status, "runtime job status", 64),
    created_at: requiredTime(row.created_at, "runtime job created time"),
    updated_at: requiredTime(row.updated_at || row.created_at, "runtime job updated time"),
  };
}

function mapHumanTask(row, uid) {
  tenantValue(row, uid, "uid");
  const jobId = requiredText(row.job_id, "human task job", 200);
  const reasonCode = requiredText(row.reason_code, "human task reason", 200);
  if (!OPPORTUNITY_JOB_ID.test(jobId) || !MACHINE_ID.test(reasonCode)
    || !Number.isInteger(row.version) || row.version < 1 || row.version > 1_000_000) invalid("human task relation");
  return {
    tenant_id: uid,
    task_id: requiredText(row.task_id, "human task id", 64),
    job_id: jobId,
    reason_code: reasonCode,
    version: row.version,
    status: requiredText(row.status, "human task status", 64),
    created_at: requiredTime(row.created_at, "human task created time"),
    updated_at: requiredTime(row.updated_at || row.created_at, "human task updated time"),
  };
}

function mapReceipt(row, uid) {
  tenantValue(row, uid);
  if (!row.receipt || typeof row.receipt !== "object" || Array.isArray(row.receipt)) invalid("runtime receipt");
  const declaredKind = row.receipt.kind || row.receipt.record_type;
  const outcome = String(row.outcome || "");
  const kindlessOutcome = !declaredKind && ["failed", "reconciled_present", "reconciled_absent"].includes(outcome);
  const kind = requiredText(
    kindlessOutcome ? (outcome === "failed" ? "work_failure" : "work_reconciliation") : declaredKind,
    "runtime receipt kind",
    128,
  );
  if (!Number.isInteger(row.attempt) || row.attempt < 1) invalid("runtime receipt attempt");
  const fallbackId = `${requiredText(row.job_id, "runtime receipt job", 200)}:${row.attempt}`;
  const receipt = {
    tenant_id: uid,
    receipt_id: APPLICATION_RECEIPT_KINDS.has(kind)
      ? (safeApplicationId(row.receipt.application_external_id) || fallbackId)
      : fallbackId,
    status: requiredText(kindlessOutcome ? outcome : row.receipt.status || row.outcome || "observed", "runtime receipt status", 128),
    observed_at: requiredTime(kindlessOutcome ? row.created_at : row.receipt.observed_at || row.created_at, "runtime receipt time"),
    kind,
  };
  return receipt;
}

function mapEarning(row, uid) {
  if (!row || row.kind !== "financial_external_income") invalid("earning kind");
  if (row.verified != null && row.verified !== true) invalid("earning verification");
  let amountMinor = row.amount_minor == null
    ? null
    : requiredMoney(row.amount_minor, "earning amount");
  if (amountMinor == null && row.amount_atomic != null) {
    const atomic = requiredMoney(row.amount_atomic, "earning atomic amount");
    if (row.currency !== "USD" || !Number.isInteger(row.amount_decimals) || row.amount_decimals < 0 || row.amount_decimals > 6) {
      invalid("earning atomic amount");
    }
    const micros = BigInt(atomic) * (10n ** BigInt(6 - row.amount_decimals));
    if (micros % 10_000n !== 0n) invalid("earning atomic amount");
    amountMinor = (micros / 10_000n).toString();
  }
  if (amountMinor == null) invalid("earning amount");
  if (!CURRENCY.test(String(row.currency || ""))) invalid("earning currency");
  const entryRef = row.public_ref || row.entry_key || row.id;
  return {
    tenant_id: uid,
    entry_ref: requiredText(String(entryRef == null ? "" : entryRef), "earning reference", 256),
    kind: "financial_external_income",
    amount_minor: amountMinor,
    currency: requiredText(row.currency, "earning currency", 3),
    occurred_at: requiredTime(row.occurred_at, "earning time"),
    verified: true,
  };
}

function freezeInput(input) {
  for (const key of ["opportunities", "runtimeJobs", "generalReceipts", "applicationReceipts", "humanTasks", "earnings"]) {
    Object.freeze(input[key]);
  }
  return Object.freeze(input);
}

function runtimeStore(options = {}) {
  if (options.runtimeStore && typeof options.runtimeStore.readRuntimeSnapshot === "function") return options.runtimeStore;
  if (typeof options.runtimeQuery === "function") return createMoneyPrinterRuntimeStore({ query: options.runtimeQuery });
  throw new Error("money printer source runtime unavailable");
}

function createMoneyPrinterSource(options = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(options);
  const runtime = runtimeStore(options);
  return async function moneyPrinterSource(scope) {
    const uid = tenantFromScope(scope);
    const baseParams = { select: "uid,agent_wallet_address", uid: `eq.${uid}`, limit: "1" };
    const users = await readRows(fetchImpl, tableUrl(supaUrl, "lm_users", baseParams), supaKey, "tenant");
    if (users.length !== 1 || String(users[0].uid || "") !== uid) invalid("tenant readback");
    const wallet = String(users[0].agent_wallet_address || "").trim();

    const snapshot = await runtime.readRuntimeSnapshot(uid);
    if (!snapshot || typeof snapshot !== "object" || ["opportunities", "runtimeJobs", "humanTasks", "receipts"].some((key) => !Array.isArray(snapshot[key]))) invalid("runtime snapshot");
    const opportunities = snapshot.opportunities.map((row) => mapOpportunity(row, uid));
    const runtimeJobs = snapshot.runtimeJobs.map((row) => mapRuntimeJob(row, uid));
    const humanTasks = snapshot.humanTasks.map((row) => mapHumanTask(row, uid));
    const receipts = snapshot.receipts.map((row) => mapReceipt(row, uid));
    const earnings = wallet
      ? (await readRows(fetchImpl, tableUrl(supaUrl, "lm_agent_earnings", {
        wallet_address: `eq.${wallet}`,
        kind: "eq.financial_external_income",
        select: "public_ref,entry_key,amount_minor,currency,occurred_at,kind",
        order: "occurred_at.desc",
      }), supaKey, "earnings")).map((row) => mapEarning(row, uid))
      : [];

    return freezeInput({
      tenantId: uid,
      observedAt: new Date().toISOString(),
      opportunities,
      runtimeJobs,
      generalReceipts: receipts.filter((row) => !APPLICATION_RECEIPT_KINDS.has(row.kind)).map(({ kind, ...row }) => row),
      applicationReceipts: receipts.filter((row) => APPLICATION_RECEIPT_KINDS.has(row.kind)).map(({ kind, ...row }) => row),
      humanTasks,
      earnings,
    });
  };
}

module.exports = { createMoneyPrinterSource };
