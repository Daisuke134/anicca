#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");

const { buildRuntimeJob, enqueueJob } = require("./runtime-job-store.js");
const { runFinancialReport } = require("./financial-report-runtime.js");
const { hashChatId, sendMessage } = require("./telegram.js");

const CAPABILITY = "report.financial.telegram";
const LOOP_ID = "financial.report";
const SECRET_REF = /^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i;
const REPORT_KINDS = new Set(["daily", "weekly"]);

function requiredText(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function financialReportRef({ tenantId, kind, nowMs, force = false }) {
  const tenant = requiredText(tenantId, "financial report tenant");
  if (!REPORT_KINDS.has(kind)) throw new Error("financial report kind is invalid");
  const instant = Number(nowMs);
  if (!Number.isFinite(instant)) throw new Error("financial report instant is invalid");
  const ref = `financial-report://${encodeURIComponent(tenant)}/${kind}/${encodeURIComponent(
    new Date(instant).toISOString(),
  )}`;
  return force ? `${ref}?force=true` : ref;
}

function parseFinancialReportRef(ref) {
  let parsed;
  try {
    parsed = new URL(requiredText(ref, "financial report ref"));
  } catch {
    throw new Error("financial report ref is invalid");
  }
  const tenantId = decodeURIComponent(parsed.hostname);
  const segments = parsed.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (
    parsed.protocol !== "financial-report:"
    || segments.length !== 2
    || !REPORT_KINDS.has(segments[0])
  ) {
    throw new Error("financial report ref is invalid");
  }
  const nowMs = Date.parse(segments[1]);
  if (!Number.isFinite(nowMs)) throw new Error("financial report ref is invalid");
  return {
    tenantId,
    kind: segments[0],
    nowMs,
    force: parsed.searchParams.get("force") === "true",
  };
}

function buildFinancialReportJob(input = {}) {
  const tenantId = requiredText(input.tenantId, "financial report tenant");
  const telegramTokenRef = requiredText(input.telegramTokenRef, "Telegram secret reference");
  if (!SECRET_REF.test(telegramTokenRef)) {
    throw new Error("Telegram token must be a secret reference");
  }
  const reportRef = financialReportRef(input);
  const digest = createHash("sha256")
    .update(`${tenantId}\n${reportRef}`, "utf8")
    .digest("hex");
  return buildRuntimeJob({
    jobId: `financial-report:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "message",
    effectKey: `telegram:financial:${digest}`,
    inputRefs: {
      financial_report_ref: reportRef,
      telegram_token_ref: telegramTokenRef,
    },
    maxAttempts: 3,
  });
}

function sentAt(providerResult, fallbackMs) {
  const providerSeconds = Number(providerResult && providerResult.result && providerResult.result.date);
  if (Number.isSafeInteger(providerSeconds) && providerSeconds > 0) {
    return new Date(providerSeconds * 1000).toISOString();
  }
  return new Date(fallbackMs).toISOString();
}

async function executeFinancialReportJob(job, deps = {}) {
  if (!job || job.capability !== CAPABILITY || job.effect_class !== "message") {
    throw new Error("financial report job contract mismatch");
  }
  const inputRefs = job.input_refs || {};
  const request = parseFinancialReportRef(inputRefs.financial_report_ref);
  if (request.tenantId !== job.tenant_id) {
    throw new Error("financial report tenant scope mismatch");
  }
  if (!deps.secretProvider || typeof deps.secretProvider.get !== "function") {
    throw new Error("financial report secret provider is required");
  }
  const telegramToken = await deps.secretProvider.get(
    job.tenant_id,
    inputRefs.telegram_token_ref,
  );
  const execute = deps.runReport || runFinancialReport;
  const providerSend = deps.sendTelegram || sendMessage;
  let providerResult;
  let telegramChatId;
  let telegramDispatchStarted = false;
  let result;
  const forceReceiptBoundary = request.force
    ? {
      readReceipt: async () => null,
      claimReceipt: async () => ({ claimed: true }),
      markReceiptSent: async () => true,
      markReceiptFailed: async () => true,
    }
    : {};
  try {
    result = await execute({
      uid: job.tenant_id,
      kind: request.kind,
      nowMs: request.nowMs,
      force: request.force,
    }, {
      ...deps,
      ...forceReceiptBoundary,
      telegramToken,
      sendTelegram: async (token, chatId, body, extra) => {
        telegramChatId = String(chatId);
        telegramDispatchStarted = true;
        providerResult = await providerSend(token, chatId, body, extra);
        return providerResult;
      },
    });
  } catch (error) {
    if (telegramDispatchStarted && error && typeof error === "object") {
      error.unknownEffect = true;
    }
    throw error;
  }
  if (result.status !== "sent") {
    const reconciled = result.status === "duplicate"
      && Number.isInteger(result.telegram_message_id)
      && /^[0-9a-f]{64}$/.test(String(result.snapshot_hash || ""))
      && /^[0-9a-f]{64}$/.test(String(result.chat_id_hash || ""));
    return {
      receipt: {
        schema_version: 1,
        kind: "telegram_financial_report",
        status: result.status,
        report_kind: result.report_kind,
        period_key: result.period_key || null,
        ...(reconciled
          ? {
            chat_id_hash: result.chat_id_hash,
            message_id: result.telegram_message_id,
            snapshot_hash: result.snapshot_hash,
            sent_at: result.sent_at,
            source_freshness: result.source_freshness,
          }
          : {}),
      },
      result,
    };
  }
  if (!telegramChatId || !Number.isInteger(result.telegram_message_id)) {
    throw new Error("financial report provider receipt is incomplete");
  }
  return {
    receipt: {
      schema_version: 1,
      kind: "telegram_financial_report",
      status: "sent",
      chat_id_hash: hashChatId(telegramChatId),
      message_id: result.telegram_message_id,
      snapshot_hash: result.snapshot_hash,
      sent_at: sentAt(providerResult, request.nowMs),
      source_freshness: result.source_freshness,
    },
    result,
  };
}

function parseEnqueueArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  if (args[0] !== "enqueue") throw new Error("usage: report-job-adapter.js enqueue --uid <tenant>");
  const uidIndex = args.indexOf("--uid");
  const tenantId = uidIndex >= 0 ? String(args[uidIndex + 1] || "").trim() : "";
  if (!tenantId || tenantId.startsWith("--")) throw new Error("--uid <tenant> is required");
  const forceIndex = args.indexOf("--force");
  let force = null;
  if (forceIndex >= 0) {
    force = String(args[forceIndex + 1] || "");
    if (!["daily", "weekly", "all"].includes(force)) {
      throw new Error("--force must be daily, weekly, or all");
    }
  }
  return { tenantId, force };
}

async function enqueueFinancialReportJobs(argv, env = process.env, deps = {}) {
  const { tenantId, force } = parseEnqueueArgs(argv);
  const nowMs = deps.nowMs == null ? Date.now() : Number(deps.nowMs);
  const telegramTokenRef = String(
    env.LM_TELEGRAM_TOKEN_REF || "secret://telegram/bot-token",
  );
  const enqueue = deps.enqueueJob || enqueueJob;
  const results = [];
  for (const kind of ["daily", "weekly"]) {
    const job = buildFinancialReportJob({
      tenantId,
      kind,
      nowMs,
      force: force === "all" || force === kind,
      telegramTokenRef,
    });
    const queued = await enqueue({
      jobId: job.job_id,
      tenantId: job.tenant_id,
      loopId: job.loop_id,
      capability: job.capability,
      effectClass: job.effect_class,
      effectKey: job.effect_key,
      inputRefs: job.input_refs,
      maxAttempts: job.max_attempts,
    });
    results.push({
      created: queued.created === true,
      job_id: job.job_id,
      report_kind: kind,
    });
  }
  (deps.stdout || process.stdout).write(`${JSON.stringify(results)}\n`);
  return results;
}

if (require.main === module) {
  enqueueFinancialReportJobs(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`[financial-report-enqueue] ${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  financialReportRef,
  parseFinancialReportRef,
  buildFinancialReportJob,
  executeFinancialReportJob,
  parseEnqueueArgs,
  enqueueFinancialReportJobs,
};
