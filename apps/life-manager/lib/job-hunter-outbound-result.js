"use strict";

const { createHash } = require("node:crypto");
const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const execFileAsync = promisify(execFile);

const HEX32 = /^[0-9a-f]{32}$/;
const HEX64 = /^[0-9a-f]{64}$/;
const GMAIL_ID = /^[0-9a-f]{16,32}$/;
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");
const VERIFIED_RESULTS = new WeakSet();
const SOURCE_TIMESTAMPS = new WeakMap();

function fail() {
  throw new Error("job hunter outbound result invalid");
}

function sqlLiteral(value) {
  if (typeof value === "number") return String(value);
  return `'${String(value).replaceAll("'", "''")}'`;
}

function makeJobHunterSqliteQuery(options = {}) {
  const ledgerPath = String(options.ledgerPath || "");
  const run = options.run || (async (args) => {
    const { stdout } = await execFileAsync(options.bin || "sqlite3", args, {
      encoding: "utf8", timeout: 15_000,
    });
    return stdout;
  });
  if (!ledgerPath.startsWith("/") || typeof run !== "function") fail();
  return async (sql, params = []) => {
    let index = 0;
    const bound = String(sql).replace(/\?/g, () => {
      if (index >= params.length) fail();
      return sqlLiteral(params[index++]);
    });
    if (index !== params.length) fail();
    const text = await run(["-readonly", "-json", ledgerPath, bound]);
    const rows = String(text).trim() ? JSON.parse(String(text)) : [];
    if (!Array.isArray(rows)) fail();
    return { rows };
  };
}

async function readJobHunterConfirmationReceipts(options = {}) {
  if (typeof options.query !== "function") fail();
  const result = await options.query(`
    SELECT confirmations.message_id,confirmations.thread_id,
      confirmations.intent_id,intents.fence,intents.application_id,
      confirmations.evidence_sha256,confirmations.received_at
    FROM submission_confirmations AS confirmations
    JOIN submit_intents AS intents ON intents.intent_id=confirmations.intent_id
    ORDER BY confirmations.received_at,confirmations.message_id
  `, []);
  if (!result || !Array.isArray(result.rows)) fail();
  return result.rows.map((row) => Object.freeze({
    message_id: String(row.message_id), thread_id: String(row.thread_id),
    intent_id: String(row.intent_id), fence: Number(row.fence),
    application_id: String(row.application_id),
    evidence_sha256: String(row.evidence_sha256), received_at: String(row.received_at),
  }));
}

function buildJobHunterConfirmationResult(input = {}) {
  const tenantId = String(input.tenantId || "");
  const receipt = input.sourceReceipt || {};
  const fence = Number(receipt.fence);
  const receivedAt = String(receipt.received_at || "");
  if (!tenantId || !HEX32.test(String(receipt.intent_id || ""))
    || !Number.isSafeInteger(fence) || fence < 1
    || !HEX64.test(String(receipt.application_id || ""))
    || !GMAIL_ID.test(String(receipt.message_id || ""))
    || !GMAIL_ID.test(String(receipt.thread_id || ""))
    || !HEX64.test(String(receipt.evidence_sha256 || ""))
    || !Number.isFinite(Date.parse(receivedAt))) fail();
  const fields = {
    schema_version: 1, tenant_id: tenantId, organ: "job_hunter",
    workflow: "job_application", source_kind: "job_submit_intent",
    source_id: `job-intent:${receipt.intent_id}`, source_fence: fence,
    entity_id: receipt.application_id, result_type: "confirmation", status: "confirmed",
    provider_message_id: receipt.message_id, provider_thread_id: receipt.thread_id,
    occurred_at: new Date(receivedAt).toISOString(),
    sender_sha256: null, subject_sha256: null, body_sha256: null,
    message_sha256: sha(JSON.stringify([receipt.message_id, receipt.thread_id,
      new Date(receivedAt).toISOString(), receipt.evidence_sha256])),
    evidence_sha256: receipt.evidence_sha256,
    rationale_sha256: sha("verified_job_hunter_submission_confirmation"),
  };
  const result = Object.freeze({
    ...fields, result_id: `outbound-result:${sha(JSON.stringify(fields))}`,
  });
  VERIFIED_RESULTS.add(result);
  // SQLite stores Python's exact datetime.isoformat() text. Keep that private
  // source identity while exposing the canonical instant to PostgreSQL.
  SOURCE_TIMESTAMPS.set(result, receivedAt);
  return result;
}

function isVerifiedJobHunterOutboundResult(value) {
  return !!(value && typeof value === "object" && VERIFIED_RESULTS.has(value));
}

async function verifyJobHunterConfirmationResultSource(value, options = {}) {
  if (!isVerifiedJobHunterOutboundResult(value)
    || value.organ !== "job_hunter" || value.workflow !== "job_application"
    || value.source_kind !== "job_submit_intent"
    || typeof options.query !== "function") fail();
  const intentId = String(value.source_id || "").replace(/^job-intent:/, "");
  if (!HEX32.test(intentId)) fail();
  const result = await options.query(`
    SELECT 1 AS verified
    FROM submission_confirmations AS confirmations
    JOIN submit_intents AS intents ON intents.intent_id=confirmations.intent_id
    WHERE confirmations.message_id=? AND confirmations.thread_id=?
      AND confirmations.intent_id=? AND intents.fence=?
      AND intents.application_id=? AND confirmations.evidence_sha256=?
      AND confirmations.received_at=?
  `, [value.provider_message_id, value.provider_thread_id, intentId,
    value.source_fence, value.entity_id, value.evidence_sha256,
    SOURCE_TIMESTAMPS.get(value)]);
  return !!(result && Array.isArray(result.rows) && result.rows.length === 1);
}

module.exports = {
  buildJobHunterConfirmationResult,
  verifyJobHunterConfirmationResultSource,
  isVerifiedJobHunterOutboundResult,
  makeJobHunterSqliteQuery,
  readJobHunterConfirmationReceipts,
};
