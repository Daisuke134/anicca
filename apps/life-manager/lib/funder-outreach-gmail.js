"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const HEX_ID = /^[0-9a-f]{16,32}$/i;

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
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    if (!result || result.status !== 0) throw new Error(String(result && result.stderr || "Gmail send failed").trim());
    return String(result.stdout || "");
  } finally {
    try { fs.unlinkSync(bodyPath); } catch {}
    try { fs.rmdirSync(root); } catch {}
  }
}

async function deliverFunderOutreachBatch(batch, dependencies = {}) {
  if (!batch || batch.schema_version !== 1 || !Array.isArray(batch.messages)
    || batch.messages.length !== batch.daily_target || batch.messages.length < 3 || batch.messages.length > 5) {
    throw new Error("funder outreach delivery invalid");
  }
  const send = dependencies.send || sendGog;
  const receipts = [];
  for (const message of batch.messages) {
    const response = await send(message, { account: dependencies.account });
    const ids = parseIds(response);
    const sentMs = Date.parse(String((dependencies.observedAt || (() => new Date().toISOString()))()));
    if (!Number.isFinite(sentMs)) throw new Error("funder outreach delivery time invalid");
    receipts.push(Object.freeze({
      schema_version: 1,
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
      subject_sha256: message.subject_sha256,
      body_sha256: message.body_sha256,
      sent_at: new Date(sentMs).toISOString(),
      provider_message_id: ids.messageId,
      provider_thread_id: ids.threadId,
    }));
  }
  return Object.freeze(receipts);
}

module.exports = { parseIds, sendGog, deliverFunderOutreachBatch };
