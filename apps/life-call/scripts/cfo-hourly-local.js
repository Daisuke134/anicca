"use strict";

const { readMoneytreeViaCodex } = require("./cfo-moneytree-codex-read.js");
const { recoverMoneytreeRead } = require("../lib/cfo-moneytree-recovery.js");
const { resolveCfoDailyRun } = require("../lib/cfo-daily-run.js");
const { appendCfoDailySnapshot } = require("../lib/cfo-daily-snapshot-store.js");
const { buildCfoDailyReport } = require("../lib/cfo-daily-snapshot.js");
const { buildCfoDailyReportFromRecovery } = require("../lib/cfo-recovery-snapshot.js");
const { renderCfoTelegram } = require("../lib/cfo-telegram.js");
const { deliverCfoTelegram } = require("../lib/cfo-telegram-send.js");
const { createCfoSupabaseRpc } = require("../lib/cfo-supabase-rpc.js");
const { runLocalAgentUsageCollection } = require("../lib/cfo-local-agent-usage-runner.js");

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const rpc = createCfoSupabaseRpc("cfo_hourly_local_failed:");

function pick(options, name, fallback) { return typeof options[name] === "function" ? options[name] : fallback; }
function ownerDate(value) { const parts = new Intl.DateTimeFormat("en", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(value); const get = (type) => parts.find((part) => part.type === type).value; return `${get("year")}-${get("month")}-${get("day")}`; }
function config(options, env) {
  const value = { uid: options.uid || options.ownerUid || env.LM_CFO_UID || env.LM_UID || env.LM_OWNER_UID, chatId: options.chatId || options.telegramChatId || env.LM_CFO_TELEGRAM_CHAT_ID || env.LM_ADMIN_TELEGRAM_CHAT_ID, telegramToken: options.telegramToken || env.LM_TELEGRAM_BOT_TOKEN, supaUrl: options.supaUrl || env.SUPABASE_URL, supaKey: options.supaKey || env.SUPABASE_SERVICE_ROLE_KEY, uidSecret: env.LM_UID_SECRET, fetchImpl: options.fetchImpl || globalThis.fetch };
  if (Object.values(value).some((item) => typeof item !== "string" && item !== value.fetchImpl) || typeof value.fetchImpl !== "function") throw new Error("config");
  if (!value.uid || !value.chatId || !value.telegramToken || !value.supaUrl || !value.supaKey || typeof value.uidSecret !== "string" || value.uidSecret.length < 32) throw new Error("config");
  return value;
}
function summary(status, reportingDate, revision, appended = false, delivered = false, recovered = false) { return { status, reportingDate, revision, appended, delivered, recovered }; }
function ordered(value) { return Array.isArray(value) ? value.map(ordered) : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, ordered(value[key])])) : value; }
function facts(report) { return JSON.stringify(ordered({ state: report.state, action: report.action && { kind: report.action.kind }, currency: report.currency, totals: report.totals, sources: report.sources.map(({ sourceId, status, amountMinor, verificationStatus }) => ({ sourceId, status, amountMinor, verificationStatus })), excluded: report.excluded })); }
function sameFacts(left, right) { return facts(left) === facts(right); }
function validateRow(row, date, render = renderCfoTelegram) {
  const keys = row && typeof row === "object" && !Array.isArray(row) ? Object.keys(row) : [];
  if (keys.length !== 5 || keys.some((key) => !["public_ref", "reporting_date", "run_id", "revision", "report_payload"].includes(key)) || !UUID.test(row.public_ref) || !UUID.test(row.run_id) || row.reporting_date !== date || !Number.isSafeInteger(row.revision) || row.revision < 1 || !row.report_payload || typeof row.report_payload !== "object") throw new Error("snapshot");
  if (row.report_payload.reportingDate !== date || row.report_payload.revision !== row.revision) throw new Error("snapshot");
  render({ locale: "ja", view: "summary", snapshot: row.report_payload });
  return row;
}
async function latestSnapshot(value, render = renderCfoTelegram) {
  const endpoint = `${value.supaUrl.replace(/\/+$/, "")}/rest/v1/lm_cfo_daily_snapshots?uid=eq.${encodeURIComponent(value.uid)}&reporting_date=eq.${value.reportingDate}&select=public_ref,reporting_date,run_id,revision,report_payload&order=revision.desc&limit=1`;
  const response = await value.fetchImpl(endpoint, { method: "GET", headers: { apikey: value.supaKey, Authorization: `Bearer ${value.supaKey}` } });
  if (!response || response.ok !== true || typeof response.json !== "function") throw new Error("snapshot");
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length > 1) throw new Error("snapshot");
  return rows.length ? validateRow(rows[0], value.reportingDate, render) : null;
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
    if (latest && sameFacts(latest.report_payload, currentBundle.report)) {
      const delivered = await send({ uid: value.uid, telegramToken: value.telegramToken, chatId: value.chatId, snapshotPublicRef: latest.public_ref, snapshot: latest.report_payload }, rpcOptions);
      if (!delivered || !["sent", "already_sent", "reconcile"].includes(delivered.status)) throw new Error("delivery");
      return summary(delivered.status === "sent" ? "sent" : delivered.status === "reconcile" ? "retry" : "quiet", reportingDate, latest.revision, false, delivered.status === "sent", recovery.status === "recovered");
    }
    const report = latest ? currentBundle.report : buildCfoDailyReport({ reportingDate, moneytreeRead: recovery.moneytreeRead });
    render({ locale: "ja", view: "summary", snapshot: report });
    const append = latest ? pick(options, "appendCfoDailySnapshotRevision", appendRevision) : pick(options, "appendCfoDailySnapshot", appendCfoDailySnapshot);
    const receipt = await append(latest ? { uid: value.uid, reportingDate, runId: run.run_id, revision: nextRevision, supersedesRevision: latest.revision, report, sourceBundle: currentBundle.sourceBundle } : { uid: value.uid, reportingDate, runId: run.run_id, moneytreeRead: recovery.moneytreeRead }, rpcOptions);
    if (!receipt || receipt.reporting_date !== reportingDate || receipt.run_id !== run.run_id || receipt.revision !== nextRevision || !UUID.test(receipt.public_ref)) throw new Error("receipt");
    const delivered = await send({ uid: value.uid, telegramToken: value.telegramToken, chatId: value.chatId, snapshotPublicRef: receipt.public_ref, snapshot: report }, rpcOptions);
    if (!delivered || !["sent", "already_sent", "reconcile"].includes(delivered.status)) throw new Error("delivery");
    return summary(delivered.status === "sent" ? "sent" : delivered.status === "reconcile" ? "retry" : "quiet", reportingDate, nextRevision, true, delivered.status === "sent", recovery.status === "recovered");
  } catch { return summary("failed", reportingDate, null, false, false, false); }
}
async function main(options = {}) { try { const env = options.env || process.env, now = options.now, usage = pick(options, "runLocalAgentUsageCollection", runLocalAgentUsageCollection); await usage({ env, ...(typeof now === "function" ? { now } : {}) }); } catch {} const result = await runHourlyCfo(options); const stdout = options && typeof options.stdout === "function" ? options.stdout : (line) => process.stdout.write(`${line}\n`); stdout(JSON.stringify(result)); return { exitCode: ["sent", "quiet"].includes(result.status) ? 0 : 1, summary: result }; }

if (require.main === module) main().then((result) => { process.exitCode = result.exitCode; });

module.exports = { runHourlyCfo, main };
