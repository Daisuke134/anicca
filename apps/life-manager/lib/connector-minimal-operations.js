"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { notifyOpenClawGateway, parseOpenClawMessageId } = require("./outbound-guardian.js");

const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9:._-]{2,159}$/;
const SAFE_REASON = /^[a-z0-9][a-z0-9_:-]{1,99}$/;
const SAFE_METHOD = /^[a-z][a-z0-9_]{1,63}$/;
const PURPOSE = /^(?:navigate|observe|fill|submit|readback)$/;
const RESULT = /^(?:success|failed)$/;
const REPORT_KEYS = "consecutive_failure_count,created_at,safe_reason,schema_version,status,wake_id";
const DELIVERY_KEYS = "delivered_at,schema_version,telegram_provider_id,wake_id";
const POSITIVE_PROVIDER_ID = /^[1-9][0-9]*$/;
const STATUSES = new Set(["applied_bundle", "completed_no_effect", "circuit_open"]);

function invalid() {
  throw new Error("Connector minimal operations invalid");
}

function exactInstant(value) {
  const instant = value instanceof Date ? value.toISOString() : String(value || "");
  if (!Number.isFinite(Date.parse(instant)) || new Date(Date.parse(instant)).toISOString() !== instant) invalid();
  return instant;
}

function privateDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.chmodSync(directory, 0o700);
  return directory;
}

function readRows(file) {
  let source = "";
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size > 5_000_000) invalid();
    source = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  return source.split(/\r?\n/).filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { invalid(); }
  });
}

function append(file, value) {
  fs.appendFileSync(file, `${JSON.stringify(value)}\n`, { encoding: "utf8", mode: 0o600 });
  fs.chmodSync(file, 0o600);
}

function safeAction(input) {
  if (
    !input || typeof input !== "object" || Array.isArray(input)
    || Object.keys(input).sort().join(",") !== "duration_ms,method,purpose,result,timestamp"
    || !PURPOSE.test(String(input.purpose || ""))
    || !SAFE_METHOD.test(String(input.method || ""))
    || !RESULT.test(String(input.result || ""))
    || !Number.isInteger(input.duration_ms) || input.duration_ms < 0 || input.duration_ms > 600_000
  ) invalid();
  return Object.freeze({
    purpose: input.purpose,
    method: input.method,
    timestamp: exactInstant(input.timestamp),
    result: input.result,
    duration_ms: input.duration_ms,
  });
}

function safeReport(input, wakeId, createdAt) {
  if (
    !input || typeof input !== "object" || Array.isArray(input)
    || !STATUSES.has(String(input.status || ""))
    || !SAFE_REASON.test(String(input.safe_reason || ""))
    || !Number.isInteger(input.consecutive_failure_count)
    || input.consecutive_failure_count < 0 || input.consecutive_failure_count > 3
  ) invalid();
  return Object.freeze({
    schema_version: 1,
    wake_id: wakeId,
    status: input.status,
    safe_reason: input.safe_reason,
    consecutive_failure_count: input.consecutive_failure_count,
    created_at: createdAt,
  });
}

function safeDelivery(input) {
  if (
    !input || typeof input !== "object" || Array.isArray(input)
    || Object.keys(input).sort().join(",") !== DELIVERY_KEYS
    || input.schema_version !== 1
    || typeof input.wake_id !== "string" || !SAFE_ID.test(input.wake_id)
    || typeof input.telegram_provider_id !== "string" || !POSITIVE_PROVIDER_ID.test(input.telegram_provider_id)
    || !Number.isSafeInteger(Number(input.telegram_provider_id))
    || typeof input.delivered_at !== "string" || exactInstant(input.delivered_at) !== input.delivered_at
  ) invalid();
  return Object.freeze({ ...input });
}

function safeDiscoveryAudit(input, wakeId, recordedAt) {
  const keys = [
    "calendar_free_count", "free_open_count", "normalized_count", "observed_count", "window_count",
  ];
  if (
    !input || typeof input !== "object" || Array.isArray(input)
    || Object.keys(input).sort().join(",") !== keys.join(",")
    || keys.some((key) => !Number.isInteger(input[key]) || input[key] < 0 || input[key] > 500)
    || input.normalized_count > input.observed_count
    || input.window_count > input.normalized_count
    || input.free_open_count > input.window_count
    || input.calendar_free_count > input.free_open_count
  ) invalid();
  return Object.freeze({
    schema_version: 1,
    wake_id: wakeId,
    ...input,
    recorded_at: recordedAt,
  });
}

function reportMessage(row) {
  const label = row.status === "applied_bundle" ? "申込と証拠保存が完了"
    : row.status === "circuit_open" ? "安全停止" : "今回の新規申込なし";
  return [
    `Connector::: ${label}`,
    `status: ${row.status}`,
    `safe reason: ${row.safe_reason}`,
    `consecutive failures: ${row.consecutive_failure_count}`,
  ].join("\n");
}

function createMinimalProductionOperations(options = {}) {
  const stateDir = privateDirectory(options.stateDir);
  const wakeId = String(options.wakeId || "");
  const telegramTarget = String(options.telegramTarget || "").trim();
  const now = options.now || (() => new Date());
  const sendMessage = options.sendMessage || notifyOpenClawGateway;
  if (
    !SAFE_ID.test(wakeId) || !telegramTarget || telegramTarget.length > 200
    || typeof now !== "function" || typeof sendMessage !== "function"
  ) invalid();
  const historyFile = path.join(stateDir, "action-history.jsonl");
  const reportFile = path.join(stateDir, "wake-reports.jsonl");
  const deliveryFile = path.join(stateDir, "wake-report-deliveries.jsonl");
  const discoveryAuditFile = path.join(stateDir, "luma-discovery-audits.jsonl");
  const connpassDiscoveryAuditFile = path.join(stateDir, "connpass-discovery-audits.jsonl");
  const peatixDiscoveryAuditFile = path.join(stateDir, "peatix-discovery-audits.jsonl");
  const meetupDiscoveryAuditFile = path.join(stateDir, "meetup-discovery-audits.jsonl");

  async function recordAction(input) {
    const action = safeAction(input);
    append(historyFile, Object.freeze({ schema_version: 1, wake_id: wakeId, ...action }));
  }

  async function recordDiscoveryAudit(input) {
    append(discoveryAuditFile, safeDiscoveryAudit(input, wakeId, exactInstant(now())));
  }

  async function recordConnpassDiscoveryAudit(input) {
    append(connpassDiscoveryAuditFile, safeDiscoveryAudit(input, wakeId, exactInstant(now())));
  }

  async function recordPeatixDiscoveryAudit(input) {
    append(peatixDiscoveryAuditFile, safeDiscoveryAudit(input, wakeId, exactInstant(now())));
  }

  async function recordMeetupDiscoveryAudit(input) {
    append(meetupDiscoveryAuditFile, safeDiscoveryAudit(input, wakeId, exactInstant(now())));
  }

  async function reportWake(input) {
    let report = safeReport(input, wakeId, exactInstant(now()));
    const reports = readRows(reportFile);
    const existing = reports.find((row) => row && row.wake_id === wakeId);
    if (existing) {
      const createdAt = exactInstant(existing.created_at);
      const canonical = safeReport(input, wakeId, createdAt);
      if (Object.keys(existing).sort().join(",") !== REPORT_KEYS
        || REPORT_KEYS.split(",").some((key) => existing[key] !== canonical[key])) invalid();
      report = canonical;
    } else {
      append(reportFile, report);
      reports.push(report);
    }
    const deliveries = readRows(deliveryFile);
    const byWake = new Map(deliveries.map((row) => {
      const delivery = safeDelivery(row);
      return [delivery.wake_id, delivery];
    }));
    async function deliver(pending) {
      if (!pending || !SAFE_ID.test(String(pending.wake_id || ""))) invalid();
      const response = await sendMessage(reportMessage(pending), { telegramTarget, idempotencyKey: pending.wake_id });
      const providerId = parseOpenClawMessageId(response);
      const delivery = safeDelivery({
        schema_version: 1,
        wake_id: pending.wake_id,
        telegram_provider_id: providerId,
        delivered_at: exactInstant(now()),
      });
      append(deliveryFile, delivery);
      byWake.set(pending.wake_id, delivery);
    }
    const current = reports.find((row) => row && row.wake_id === wakeId);
    if (!current) invalid();
    if (!byWake.has(wakeId)) await deliver(current);
    let historical;
    for (const pending of reports) {
      if (!pending || !SAFE_ID.test(String(pending.wake_id || ""))) invalid();
      if (pending.wake_id !== wakeId && !byWake.has(pending.wake_id)) {
        historical = pending;
        break;
      }
    }
    if (historical) {
      try { await deliver(historical); } catch {}
    }
    const currentDelivery = byWake.get(wakeId);
    if (!currentDelivery) invalid();
    return Object.freeze({ telegram_provider_id: currentDelivery.telegram_provider_id });
  }

  return Object.freeze({
    recordAction, recordDiscoveryAudit, recordConnpassDiscoveryAudit, recordPeatixDiscoveryAudit,
    recordMeetupDiscoveryAudit, reportWake,
  });
}

module.exports = { createMinimalProductionOperations };
