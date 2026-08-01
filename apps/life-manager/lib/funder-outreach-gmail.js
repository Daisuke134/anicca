"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { isVerifiedInvestorOutreachReservation } = require("./funder-investor-outreach.js");
const { isVerifiedFunderOutreachBatch } = require("./funder-outreach.js");

const HEX_ID = /^[0-9a-f]{16,32}$/i;
const VERIFIED_V2_RECEIPTS = new WeakSet();

function parseIds(result) {
  let value = result;
  if (typeof result === "string") {
    try { value = JSON.parse(result); } catch { value = null; }
  }
  const messageId = String(value && (value.message_id || value.messageId) || "");
  const threadId = String(value && (value.thread_id || value.threadId) || "");
  if (!HEX_ID.test(messageId) || !HEX_ID.test(threadId)) throw new Error("Gmail message/thread ID required");
  return { messageId: messageId.toLowerCase(), threadId: threadId.toLowerCase() };
}

async function sendGog(message, options = {}) {
  const account = String(options.account || "").trim();
  if (!account) throw new Error("Gmail account required");
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-funder-outreach-"));
  const bodyPath = path.join(root, "body.txt");
  try {
    fs.writeFileSync(bodyPath, `${message.body}\n`, { mode: 0o600 });
    const result = (options.spawnSync || spawnSync)("gog", [
      "gmail", "send", "--account", account, "--to", message.recipient,
      "--subject", message.subject, "--body-file", bodyPath, "--json",
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 30_000 });
    if (!result || result.status !== 0) throw new Error(String(result && result.stderr || "Gmail send failed").trim());
    return String(result.stdout || "");
  } finally {
    try { fs.unlinkSync(bodyPath); } catch {}
    try { fs.rmdirSync(root); } catch {}
  }
}

async function deliverFunderOutreachBatch(batch, dependencies = {}) {
  if (!batch || !Array.isArray(batch.messages)) {
    throw new Error("funder outreach delivery invalid");
  }
  if (batch.schema_version === 1) {
    if (!isVerifiedFunderOutreachBatch(batch) || batch.messages.length !== batch.daily_target
      || batch.messages.length < 3 || batch.messages.length > 5) {
      throw new Error("funder outreach delivery invalid");
    }
    throw new Error("funder outreach legacy delivery retired");
  } else if (batch.schema_version === 2) {
    if (batch.reserved !== true || !isVerifiedInvestorOutreachReservation(batch)) {
      throw new Error("funder outreach reservation required");
    }
    if (!Number.isInteger(batch.existing_count) || !Number.isInteger(batch.daily_target)
      || batch.daily_target < 3 || batch.daily_target > 5
      || batch.messages.length !== Math.max(0, batch.daily_target - batch.existing_count)
      || batch.existing_count + batch.messages.length > 5
      || batch.messages.some((message) => !["vc", "angel"].includes(message.investor_kind)
        || !Number.isInteger(message.daily_slot) || message.daily_slot < 1 || message.daily_slot > 5
        || !Number.isFinite(Date.parse(message.reserved_at))
        || ![message.thesis_evidence_sha256, message.company_evidence_sha256,
          message.personalization_sha256].every((value) => /^[0-9a-f]{64}$/.test(String(value || ""))))) {
      throw new Error("funder outreach delivery invalid");
    }
  } else {
    throw new Error("funder outreach delivery invalid");
  }
  const sentMs = Date.parse(String((dependencies.observedAt || (() => new Date().toISOString()))()));
  if (!Number.isFinite(sentMs) || !Number.isFinite(Date.parse(batch.strategy_valid_until))
    || sentMs >= Date.parse(batch.strategy_valid_until)) {
    throw new Error("funder outreach strategy expired before delivery");
  }
  const send = dependencies.send || sendGog;
  const receipts = [];
  for (const message of batch.messages) {
    const response = await send(message, { account: dependencies.account });
    const ids = parseIds(response);
    const receipt = Object.freeze({
      schema_version: batch.schema_version,
      outreach_id: message.outreach_id,
      batch_id: batch.batch_id,
      tenant_id: batch.tenant_id,
      tokyo_date: batch.tokyo_date,
      candidate_id: message.candidate_id,
      funder_name: message.funder_name,
      recipient_sha256: message.recipient_sha256,
      source_url: message.source_url,
      source_observed_at: message.source_observed_at,
      source_digest: message.source_digest,
      fit_summary_sha256: message.fit_summary_sha256,
      ...(batch.schema_version === 2 ? {
        investor_kind: message.investor_kind,
        thesis_evidence_sha256: message.thesis_evidence_sha256,
        company_evidence_sha256: message.company_evidence_sha256,
        personalization_sha256: message.personalization_sha256,
        daily_slot: message.daily_slot,
        ...(message.reflection_id ? {
          reflection_id: message.reflection_id,
          reflection_week_key: message.reflection_week_key,
          ranking_position: message.ranking_position,
          pitch_directive_sha256: message.pitch_directive_sha256,
          reflection_outcome_result_ids: message.reflection_outcome_result_ids,
        } : {}),
      } : {}),
      subject_sha256: message.subject_sha256,
      body_sha256: message.body_sha256,
      sent_at: new Date(sentMs).toISOString(),
      provider_message_id: ids.messageId,
      provider_thread_id: ids.threadId,
    });
    if (receipt.schema_version === 2) VERIFIED_V2_RECEIPTS.add(receipt);
    receipts.push(receipt);
  }
  return Object.freeze(receipts);
}

function isVerifiedFunderReflectionOutreachReceipt(value) {
  return Boolean(value && VERIFIED_V2_RECEIPTS.has(value));
}

module.exports = {
  parseIds,
  sendGog,
  deliverFunderOutreachBatch,
  isVerifiedFunderReflectionOutreachReceipt,
};
