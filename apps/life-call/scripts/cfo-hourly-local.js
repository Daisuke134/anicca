"use strict";

const os = require("node:os");
const path = require("node:path");
const { readMoneytreeViaCodex } = require("./cfo-moneytree-codex-read.js");
const { recoverMoneytreeRead } = require("../lib/cfo-moneytree-recovery.js");
const { resolveCfoDailyRun } = require("../lib/cfo-daily-run.js");
const { buildCfoDailyReportFromRecovery } = require("../lib/cfo-recovery-snapshot.js");
const { renderCfoTelegram } = require("../lib/cfo-telegram.js");
const { deliverCfoTelegram } = require("../lib/cfo-telegram-send.js");
const { createCfoSupabaseRpc } = require("../lib/cfo-supabase-rpc.js");
const { runLocalAgentUsageCollection } = require("../lib/cfo-local-agent-usage-runner.js");
const { makeGogMail } = require("../lib/transport/mail-gog.js");
const { captureLatestGoogleCloudInvoice } = require("../lib/cfo-google-invoice-local-source.js");
const { captureLatestAnthropicSubscriptionReceipt } = require("../lib/cfo-anthropic-receipt-local-source.js");

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const rpc = createCfoSupabaseRpc("cfo_hourly_local_failed:");
const AI_COST_KEYS = ["provider", "plan", "amount", "currency", "billingPeriodStart", "billingPeriodEnd", "evidenceStatus", "unavailableProviders"];
const RECEIPT_KEYS = ["schema_version", "provider", "plan", "billing_period_start", "billing_period_end", "subtotal", "tax", "total", "currency", "paid_date", "source_hash", "evidence_status"];

function pick(options, name, fallback) { return typeof options[name] === "function" ? options[name] : fallback; }
function ownerDate(value) { const parts = new Intl.DateTimeFormat("en", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(value); const get = (type) => parts.find((part) => part.type === type).value; return `${get("year")}-${get("month")}-${get("day")}`; }
function ownerHour(value) { const parts = new Intl.DateTimeFormat("en", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23" }).formatToParts(value); const get = (type) => parts.find((part) => part.type === type).value; return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}`; }
function config(options, env) {
  const value = { uid: options.uid || options.ownerUid || env.LM_CFO_UID || env.LM_UID || env.LM_OWNER_UID, chatId: options.chatId || options.telegramChatId || env.LM_CFO_TELEGRAM_CHAT_ID || env.LM_ADMIN_TELEGRAM_CHAT_ID, telegramToken: options.telegramToken || env.LM_TELEGRAM_BOT_TOKEN, supaUrl: options.supaUrl || env.SUPABASE_URL, supaKey: options.supaKey || env.SUPABASE_SERVICE_ROLE_KEY, uidSecret: env.LM_UID_SECRET, fetchImpl: options.fetchImpl || globalThis.fetch };
  if (Object.values(value).some((item) => typeof item !== "string" && item !== value.fetchImpl) || typeof value.fetchImpl !== "function") throw new Error("config");
  if (!value.uid || !value.chatId || !value.telegramToken || !value.supaUrl || !value.supaKey || typeof value.uidSecret !== "string" || value.uidSecret.length < 32) throw new Error("config");
  return value;
}
function summary(status, reportingDate, revision, appended = false, delivered = false, recovered = false) { return { status, reportingDate, revision, appended, delivered, recovered }; }
function ordered(value) { return Array.isArray(value) ? value.map(ordered) : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, ordered(value[key])])) : value; }
function facts(report) { return JSON.stringify(ordered({ state: report.state, action: report.action && { kind: report.action.kind }, currency: report.currency, totals: report.totals, sources: report.sources.map(({ sourceId, status, amountMinor, verificationStatus }) => ({ sourceId, status, amountMinor, verificationStatus })), excluded: report.excluded, aiCost: report.aiCost || null })); }
function sameFacts(left, right) { return facts(left) === facts(right); }
function validateRow(row, date, render = renderCfoTelegram) {
  const keys = row && typeof row === "object" && !Array.isArray(row) ? Object.keys(row) : [];
  if (keys.length !== 6 || keys.some((key) => !["public_ref", "reporting_date", "run_id", "revision", "created_at", "report_payload"].includes(key)) || !UUID.test(row.public_ref) || !UUID.test(row.run_id) || row.reporting_date !== date || !Number.isSafeInteger(row.revision) || row.revision < 1 || typeof row.created_at !== "string" || !rpc.timestamp(row.created_at) || !row.report_payload || typeof row.report_payload !== "object") throw new Error("snapshot");
  if (row.report_payload.reportingDate !== date || row.report_payload.revision !== row.revision) throw new Error("snapshot");
  render({ locale: "ja", view: "summary", snapshot: row.report_payload });
  return row;
}
async function latestSnapshot(value, render = renderCfoTelegram) {
  const endpoint = `${value.supaUrl.replace(/\/+$/, "")}/rest/v1/lm_cfo_daily_snapshots?uid=eq.${encodeURIComponent(value.uid)}&reporting_date=eq.${value.reportingDate}&select=public_ref,reporting_date,run_id,revision,created_at,report_payload&order=revision.desc&limit=1`;
  const response = await value.fetchImpl(endpoint, { method: "GET", headers: { apikey: value.supaKey, Authorization: `Bearer ${value.supaKey}` } });
  if (!response || response.ok !== true || typeof response.json !== "function") throw new Error("snapshot");
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length > 1) throw new Error("snapshot");
  return rows.length ? validateRow(rows[0], value.reportingDate, render) : null;
}
async function latestAiCostSnapshot(value, render = renderCfoTelegram) {
  const endpoint = `${value.supaUrl.replace(/\/+$/, "")}/rest/v1/lm_cfo_daily_snapshots?uid=eq.${encodeURIComponent(value.uid)}&reporting_date=lt.${encodeURIComponent(value.reportingDate)}&report_payload->aiCost=not.is.null&select=public_ref,reporting_date,run_id,revision,created_at,report_payload&order=created_at.desc&limit=1`;
  const response = await value.fetchImpl(endpoint, { method: "GET", headers: { apikey: value.supaKey, Authorization: `Bearer ${value.supaKey}` } });
  if (!response || response.ok !== true || typeof response.json !== "function") throw new Error("snapshot");
  const rows = await response.json(); if (!Array.isArray(rows) || rows.length > 1) throw new Error("snapshot");
  if (!rows.length) return null; const row = rows[0]; return validateRow(row, row.reporting_date, render);
}
async function appendRevision(input, value) {
  const options = { supaUrl: value.supaUrl, supaKey: value.supaKey, fetchImpl: value.fetchImpl };
  const parsed = await rpc.postRpc(rpc.validateOptions(options), "lm_append_cfo_daily_snapshot_revision", { p_uid: input.uid, p_reporting_date: input.reportingDate, p_run_id: input.runId, p_revision: input.revision, p_supersedes_revision: input.supersedesRevision, p_report_payload: input.report, p_source_bundle: input.sourceBundle });
  const keys = parsed && typeof parsed === "object" ? Object.keys(parsed) : [];
  if (keys.length !== 6 || keys.some((key) => !["public_ref", "reporting_date", "run_id", "revision", "supersedes_revision", "created_at"].includes(key)) || !UUID.test(parsed.public_ref) || parsed.reporting_date !== input.reportingDate || parsed.run_id !== input.runId || parsed.revision !== input.revision || parsed.supersedes_revision !== input.supersedesRevision || typeof parsed.created_at !== "string" || !rpc.timestamp(parsed.created_at)) throw new Error("receipt");
  return parsed;
}
async function runHourlyCfo(options = {}) {
  let reportingDate = null;
  try {
    const env = options.env || process.env, clock = new Date(typeof options.now === "function" ? options.now() : (options.now || new Date()));
    if (!Number.isFinite(clock.getTime())) throw new Error("clock");
    reportingDate = ownerDate(clock);
    const value = config(options, env), rpcOptions = { supaUrl: value.supaUrl, supaKey: value.supaKey, fetchImpl: value.fetchImpl };
    const reader = pick(options, "readMoneytreeViaCodex", readMoneytreeViaCodex), recover = pick(options, "recoverMoneytreeRead", recoverMoneytreeRead);
    const recovery = await recover({ reportingDate, observedAt: clock.toISOString() }, { read: async () => { try { return { ok: true, moneytreeRead: await reader({ env, now: () => clock }) }; } catch { return { ok: false, kind: "timeout" }; } }, repair: pick(options, "repair", async () => true), wait: pick(options, "wait", (milliseconds) => new Promise((resolveWait) => setTimeout(resolveWait, milliseconds))) });
    const resolve = pick(options, "resolveCfoDailyRun", resolveCfoDailyRun), run = await resolve({ uid: value.uid }, rpcOptions);
    if (!run || run.reporting_date !== reportingDate || !UUID.test(run.run_id)) throw new Error("run");
    const render = pick(options, "renderCfoTelegram", renderCfoTelegram), send = pick(options, "deliverCfoTelegram", deliverCfoTelegram);
    const latestRaw = typeof options.latestSnapshot === "function" ? await options.latestSnapshot({ uid: value.uid, reportingDate, runId: run.run_id, ...rpcOptions }) : await latestSnapshot({ uid: value.uid, reportingDate, ...value }, render);
    const latest = latestRaw ? validateRow(latestRaw, reportingDate, render) : null;
    if (latest && (latest.run_id !== run.run_id || latest.reporting_date !== reportingDate)) throw new Error("snapshot");
    if (!latest && recovery.status === "action_required") return summary("retry", reportingDate, null, false, false, false);
    const nextRevision = latest ? latest.revision + 1 : 1;
    const currentBundle = buildCfoDailyReportFromRecovery({ revision: nextRevision, recovery });
    const aiCost = await selectAiCost(options, { ...value, reportingDate }, latest, render), candidateReport = reportWithAiCost(currentBundle.report, aiCost);
    if (latest && sameFacts(latest.report_payload, candidateReport) && ownerHour(new Date(latest.created_at)) === ownerHour(clock)) {
      const delivered = await send({ uid: value.uid, telegramToken: value.telegramToken, chatId: value.chatId, snapshotPublicRef: latest.public_ref, snapshot: latest.report_payload }, rpcOptions);
      if (!delivered || !["sent", "already_sent", "reconcile"].includes(delivered.status)) throw new Error("delivery");
      return summary(delivered.status === "sent" ? "sent" : delivered.status === "reconcile" ? "retry" : "quiet", reportingDate, latest.revision, false, delivered.status === "sent", recovery.status === "recovered");
    }
    const report = candidateReport;
    render({ locale: "ja", view: "summary", snapshot: report });
    const append = latest ? pick(options, "appendCfoDailySnapshotRevision", appendRevision) : pick(options, "appendCfoDailySnapshot", appendInitial);
    const receipt = await append(latest ? { uid: value.uid, reportingDate, runId: run.run_id, revision: nextRevision, supersedesRevision: latest.revision, report, sourceBundle: currentBundle.sourceBundle } : { uid: value.uid, reportingDate, runId: run.run_id, moneytreeRead: recovery.moneytreeRead, report, sourceBundle: currentBundle.sourceBundle }, rpcOptions);
    if (!receipt || receipt.reporting_date !== reportingDate || receipt.run_id !== run.run_id || receipt.revision !== nextRevision || !UUID.test(receipt.public_ref)) throw new Error("receipt");
    const delivered = await send({ uid: value.uid, telegramToken: value.telegramToken, chatId: value.chatId, snapshotPublicRef: receipt.public_ref, snapshot: report }, rpcOptions);
    if (!delivered || !["sent", "already_sent", "reconcile"].includes(delivered.status)) throw new Error("delivery");
    return summary(delivered.status === "sent" ? "sent" : delivered.status === "reconcile" ? "retry" : "quiet", reportingDate, nextRevision, true, delivered.status === "sent", recovery.status === "recovered");
  } catch { return summary("failed", reportingDate, null, false, false, false); }
}
const unavailableBilling = Object.freeze({ status: "unavailable", confirmedCount: 0, unresolvedCount: 0, unavailableCount: 1 });
const exactObject = (value, keys) => { try { return value && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype && Reflect.ownKeys(value).length === keys.length && keys.every(key => { const descriptor = Object.getOwnPropertyDescriptor(value, key); return descriptor && descriptor.enumerable && Object.hasOwn(value, key) && Object.hasOwn(descriptor, "value"); }); } catch { return false; } };
function validDate(value) { if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false; const date = new Date(`${value}T00:00:00Z`); return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value; }
function nextMonth(value) { const [year, month, day] = value.split("-").map(Number), next = `${String(month === 12 ? year + 1 : year).padStart(4, "0")}-${String(month === 12 ? 1 : month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`; return validDate(next) ? next : null; }
function activePeriod(start, end, date) { return validDate(start) && validDate(end) && validDate(date) && start < end && start <= date && date < end; }
function copyAiCost(value, date) { try { if (!exactObject(value, AI_COST_KEYS) || value.provider !== "anthropic" || value.plan !== "max_20x" || value.amount !== "220.00" || value.currency !== "USD" || value.evidenceStatus !== "provider_receipt" || !activePeriod(value.billingPeriodStart, value.billingPeriodEnd, date)) return null; const unavailable = value.unavailableProviders, keys = Array.isArray(unavailable) && Object.getPrototypeOf(unavailable) === Array.prototype ? Reflect.ownKeys(unavailable) : [], zero = keys.length === 2 && Object.getOwnPropertyDescriptor(unavailable, "0"), length = keys.length === 2 && Object.getOwnPropertyDescriptor(unavailable, "length"); if (!zero || !length || !Object.hasOwn(zero, "value") || !Object.hasOwn(length, "value") || !zero.enumerable || zero.value !== "openai" || length.value !== 1) return null; return Object.freeze({ provider: "anthropic", plan: "max_20x", amount: "220.00", currency: "USD", billingPeriodStart: value.billingPeriodStart, billingPeriodEnd: value.billingPeriodEnd, evidenceStatus: "provider_receipt", unavailableProviders: ["openai"] }); } catch { return null; } }
function receiptAiCost(value, date) { try { if (!exactObject(value, ["status", "record_id", "confirmed"]) || !["appended", "existing"].includes(value.status) || typeof value.record_id !== "string" || !exactObject(value.confirmed, RECEIPT_KEYS)) return null; const record = value.confirmed, start = record.billing_period_start, end = record.billing_period_end, subtotal = /^\d+\.\d{2}$/.test(record.subtotal) ? BigInt(record.subtotal.replace(".", "")) : -1n, tax = /^\d+\.\d{2}$/.test(record.tax) ? BigInt(record.tax.replace(".", "")) : -1n, total = /^\d+\.\d{2}$/.test(record.total) ? BigInt(record.total.replace(".", "")) : -1n; if (record.schema_version !== "lm_subscription_receipt_v1" || record.provider !== "anthropic" || record.plan !== "max_20x" || record.currency !== "USD" || record.evidence_status !== "provider_receipt" || record.paid_date !== start || record.source_hash !== value.record_id || !/^sha256:[0-9a-f]{64}$/.test(record.source_hash) || subtotal !== 20000n || tax !== 2000n || total !== 22000n || subtotal + tax !== total || end !== nextMonth(start) || !activePeriod(start, end, date)) return null; return copyAiCost({ provider: "anthropic", plan: "max_20x", amount: "220.00", currency: "USD", billingPeriodStart: start, billingPeriodEnd: end, evidenceStatus: "provider_receipt", unavailableProviders: ["openai"] }, date); } catch { return null; } }
function reportWithAiCost(report, aiCost) { const copy = structuredClone(report); if (aiCost) copy.aiCost = aiCost; return copy; }
async function selectAiCost(options, value, latest, render) { const current = copyAiCost(options.aiCost, value.reportingDate) || (latest && copyAiCost(latest.report_payload.aiCost, value.reportingDate)); if (current) return current; try { const candidate = typeof options.latestAiCost === "function" ? await options.latestAiCost({ uid: value.uid, reportingDate: value.reportingDate, supaUrl: value.supaUrl, supaKey: value.supaKey, fetchImpl: value.fetchImpl }) : await latestAiCostSnapshot(value, render); const row = candidate && candidate.report_payload ? validateRow(candidate, candidate.reporting_date, render) : null; return row ? copyAiCost(row.report_payload.aiCost, value.reportingDate) : copyAiCost(candidate, value.reportingDate); } catch { return null; } }
async function appendInitial(input, options) { const config = rpc.validateOptions(options), parsed = await rpc.postRpc(config, "lm_append_cfo_daily_snapshot", { p_uid: input.uid, p_reporting_date: input.reportingDate, p_run_id: input.runId, p_report_payload: input.report, p_source_bundle: input.sourceBundle }), keys = exactObject(parsed, ["public_ref", "reporting_date", "run_id", "revision", "created_at"]) ? 5 : exactObject(parsed, ["public_ref", "reporting_date", "run_id", "revision", "created_at", "supersedes_revision"]) && parsed.supersedes_revision === null ? 6 : 0; if (!keys || !UUID.test(parsed.public_ref) || parsed.reporting_date !== input.reportingDate || parsed.run_id !== input.runId || parsed.revision !== 1 || typeof parsed.created_at !== "string" || !rpc.timestamp(parsed.created_at)) throw new Error("receipt"); return { public_ref: parsed.public_ref, reporting_date: parsed.reporting_date, run_id: parsed.run_id, revision: parsed.revision, created_at: parsed.created_at }; }
function billingCounts(receipt) {
  const c = receipt && receipt.confirmed, scope = c && c.scope, amount = c && c.amount;
  const confirmed = exactObject(receipt, ["status", "record_id", "confirmed"]) && (receipt.status === "appended" || receipt.status === "existing") && typeof receipt.record_id === "string" && /^sha256:[0-9a-f]{64}$/.test(receipt.record_id) && exactObject(c, ["schema_version", "provider", "billing_period", "scope", "amount", "source", "source_document_ref", "observed_at", "evidence_status"]) && c.schema_version === 1 && c.provider === "google_cloud" && /^(?:\d{4}(?:0[1-9]|1[0-2]))$/.test(c.billing_period) && exactObject(scope, ["kind", "ref"]) && scope.kind === "billing_account" && /^sha256:[0-9a-f]{64}$/.test(scope.ref) && exactObject(amount, ["value", "currency"]) && amount.currency === "JPY" && typeof amount.value === "string" && /^(?:0|[1-9]\d*)$/.test(amount.value) && c.source === "provider_invoice_pdf" && c.source_document_ref === receipt.record_id && /^sha256:[0-9a-f]{64}$/.test(c.source_document_ref) && typeof c.observed_at === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(c.observed_at) && Number.isFinite(Date.parse(c.observed_at)) && c.evidence_status === "provider_billed";
  return confirmed ? Object.freeze({ status: "confirmed_unresolved", confirmedCount: 1, unresolvedCount: 1, unavailableCount: 0 }) : unavailableBilling;
}
async function main(options = {}) {
  const usage = options && typeof options.runLocalAgentUsageCollection === "function" ? options.runLocalAgentUsageCollection : runLocalAgentUsageCollection;
  try {
    const sourceEnv = options.env || process.env, descriptor = Object.getOwnPropertyDescriptor(sourceEnv, "LIFE_MANAGER_STATE_HOME");
    const env = descriptor && Object.hasOwn(descriptor, "value") ? { LIFE_MANAGER_STATE_HOME: descriptor.value } : {};
    await usage({ env });
  } catch {}
  const sourceEnv = options.env || process.env, clock = new Date(typeof options.now === "function" ? options.now() : (options.now || new Date())); let providerBilling = unavailableBilling, aiCost = null;
  if (sourceEnv.GOG_ACCOUNT) { let mail = null; try { mail = (typeof options.makeGogMail === "function" ? options.makeGogMail : makeGogMail)({ account: sourceEnv.GOG_ACCOUNT }); } catch {}
    if (mail) { try { const capture = typeof options.captureLatestGoogleCloudInvoice === "function" ? options.captureLatestGoogleCloudInvoice : captureLatestGoogleCloudInvoice; aiCost = null; providerBilling = billingCounts(await capture({ stateRoot: sourceEnv.LIFE_MANAGER_STATE_HOME || path.join(os.homedir(), ".local", "state", "life-manager"), observedAt: clock.toISOString(), mail })); } catch {}
      try { const capture = typeof options.captureLatestAnthropicSubscriptionReceipt === "function" ? options.captureLatestAnthropicSubscriptionReceipt : captureLatestAnthropicSubscriptionReceipt; aiCost = receiptAiCost(await capture({ stateRoot: sourceEnv.LIFE_MANAGER_STATE_HOME || path.join(os.homedir(), ".local", "state", "life-manager"), observedAt: clock.toISOString(), mail }), ownerDate(clock)); } catch {} }
  }
  const result = await runHourlyCfo({ ...options, aiCost, now: clock }); const stdout = options && typeof options.stdout === "function" ? options.stdout : (line) => process.stdout.write(`${line}\n`); stdout(JSON.stringify({ ...result, providerBilling })); return { exitCode: ["sent", "quiet"].includes(result.status) ? 0 : 1, summary: result, providerBilling }; }

if (require.main === module) main().then((result) => { process.exitCode = result.exitCode; });

module.exports = { runHourlyCfo, main };
