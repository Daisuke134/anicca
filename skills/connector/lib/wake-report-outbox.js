"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { notifyOpenClawGateway, parseOpenClawMessageId } = require("../../../apps/life-manager/lib/outbound-guardian.js");

const SAFE_ID = /^[A-Za-z0-9:._-]{1,160}$/;
const SAFE_REASON = /^[a-z0-9_:-]{1,100}$/;

function invalid() {
  throw new Error("Connector wake report outbox invalid");
}

function readRows(file, validate) {
  let source = "";
  try {
    const stat = fs.statSync(file);
    if (stat.size > 1_000_000) invalid();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  return source.split(/\r?\n/).filter(Boolean).map((line) => {
    let row;
    try { row = JSON.parse(line); } catch { invalid(); }
    validate(row);
    return row;
  });
}

function validIso(value) {
  return Number.isFinite(Date.parse(String(value || "")))
    && new Date(Date.parse(value)).toISOString() === value;
}

function validateReport(row) {
  if (
    !row || typeof row !== "object" || Array.isArray(row)
    || Object.keys(row).sort().join(",") !== "attempt_count,created_at,cursor,open_count,report_kind,safe_reason,schema_version,wake_id"
    || row.schema_version !== 1
    || !SAFE_ID.test(String(row.wake_id || ""))
    || !["applied", "continuing", "recovering"].includes(row.report_kind)
    || !SAFE_REASON.test(String(row.safe_reason || ""))
    || !SAFE_ID.test(String(row.cursor || ""))
    || !Number.isSafeInteger(row.open_count) || row.open_count < 0 || row.open_count > 28
    || !Number.isSafeInteger(row.attempt_count) || row.attempt_count < 0 || row.attempt_count > 10_000
    || !validIso(row.created_at)
  ) invalid();
}

function validateDelivery(row) {
  if (
    !row || typeof row !== "object" || Array.isArray(row)
    || Object.keys(row).sort().join(",") !== "delivered_at,schema_version,telegram_provider_id,wake_id"
    || row.schema_version !== 1
    || !SAFE_ID.test(String(row.wake_id || ""))
    || !/^[1-9][0-9]{0,19}$/.test(String(row.telegram_provider_id || ""))
    || !validIso(row.delivered_at)
  ) invalid();
}

function enqueueWakeReport(stateDir, input) {
  const file = path.join(stateDir, "wake-report-outbox.jsonl");
  const existing = readRows(file, validateReport);
  if (existing.some((row) => row.wake_id === input.wake_id)) return;
  const row = {
    schema_version: 1,
    wake_id: input.wake_id,
    report_kind: input.report_kind,
    safe_reason: input.safe_reason,
    cursor: input.cursor,
    open_count: input.open_count,
    attempt_count: input.attempt_count,
    created_at: input.created_at,
  };
  validateReport(row);
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  fs.appendFileSync(file, `${JSON.stringify(row)}\n`, { encoding: "utf8", mode: 0o600 });
}

function reportMessage(row) {
  const label = row.report_kind === "applied" ? "申込完了"
    : row.report_kind === "recovering" ? "復旧中" : "継続中";
  return [
    `Connector::: ${label}`,
    `状態: ${row.safe_reason}`,
    `未充足日: ${row.open_count}`,
    `今回の試行: ${row.attempt_count}`,
    `次の位置: ${row.cursor}`,
  ].join("\n");
}

async function deliverPendingWakeReports(stateDir, options = {}) {
  const reports = readRows(path.join(stateDir, "wake-report-outbox.jsonl"), validateReport);
  const deliveries = readRows(path.join(stateDir, "wake-report-deliveries.jsonl"), validateDelivery);
  const delivered = new Set(deliveries.map((row) => row.wake_id));
  const target = String(options.telegramTarget || "").trim();
  if (!target) return;
  const send = typeof options.send === "function" ? options.send : notifyOpenClawGateway;
  for (const report of reports) {
    if (delivered.has(report.wake_id)) continue;
    let response;
    try {
      response = await send(reportMessage(report), {
        telegramTarget: target,
        idempotencyKey: report.wake_id,
      });
    } catch {
      return;
    }
    let providerId;
    try { providerId = parseOpenClawMessageId(JSON.stringify(response || {})); }
    catch { return; }
    const receipt = {
      schema_version: 1,
      wake_id: report.wake_id,
      telegram_provider_id: providerId,
      delivered_at: report.created_at,
    };
    validateDelivery(receipt);
    fs.appendFileSync(
      path.join(stateDir, "wake-report-deliveries.jsonl"),
      `${JSON.stringify(receipt)}\n`,
      { encoding: "utf8", mode: 0o600 },
    );
    delivered.add(report.wake_id);
  }
}

async function recordProcessCrash(argv = process.argv.slice(2), env = process.env) {
  if (argv.length !== 3 || argv[0] !== "process-crash") invalid();
  const stateDir = path.resolve(String(argv[1] || ""));
  const wakeId = String(argv[2] || "");
  if (!path.isAbsolute(stateDir) || stateDir === path.parse(stateDir).root || !SAFE_ID.test(wakeId)) invalid();
  const createdAt = new Date().toISOString();
  enqueueWakeReport(stateDir, {
    wake_id: wakeId,
    report_kind: "recovering",
    safe_reason: "process_crash",
    cursor: "provider:none",
    open_count: 0,
    attempt_count: 0,
    created_at: createdAt,
  });
  await deliverPendingWakeReports(stateDir, { telegramTarget: env.LM_CONNECTOR_TELEGRAM_TARGET });
}

if (require.main === module) {
  recordProcessCrash().catch(() => {
    process.stderr.write("Connector wake report unavailable\n", () => process.exit(2));
  });
}

module.exports = { deliverPendingWakeReports, enqueueWakeReport, recordProcessCrash };
