"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { parseIds } = require("./funder-outreach-gmail.js");

async function sendGogFollowup(message, options = {}) {
  const account = String(options.account || "").trim();
  if (!account) throw new Error("Gmail account required");
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-funder-followup-"));
  const bodyPath = path.join(root, "body.txt");
  try {
    fs.writeFileSync(bodyPath, `${message.body}\n`, { mode: 0o600 });
    const result = (options.spawnSync || spawnSync)("gog", [
      "gmail", "send", "--account", account,
      "--reply-to-message-id", message.reply_to_message_id,
      "--thread-id", message.thread_id, "--reply-all",
      "--subject", message.subject, "--body-file", bodyPath, "--json", "--no-input",
    ], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    if (!result || result.status !== 0) throw new Error(String(result && result.stderr || "Gmail follow-up failed").trim());
    return String(result.stdout || "");
  } finally {
    try { fs.unlinkSync(bodyPath); } catch {}
    try { fs.rmdirSync(root); } catch {}
  }
}

async function deliverFunderFollowup(plan, dependencies = {}) {
  if (!plan || plan.status !== "due" || ![1, 2].includes(plan.followup_number)) throw new Error("funder follow-up delivery invalid");
  const response = await (dependencies.send || sendGogFollowup)(plan, { account: dependencies.account });
  let ids;
  try { ids = parseIds(response); } catch { throw new Error("Gmail message/thread ID required"); }
  if (ids.threadId !== String(plan.provider_thread_id).toLowerCase()) throw new Error("funder follow-up Gmail thread mismatch");
  const sentMs = Date.parse(String((dependencies.observedAt || (() => new Date().toISOString()))()));
  if (!Number.isFinite(sentMs) || sentMs < Date.parse(plan.due_at)) throw new Error("funder follow-up sent time invalid");
  return Object.freeze({
    schema_version: 1,
    followup_id: plan.followup_id,
    outreach_id: plan.outreach_id,
    batch_id: plan.batch_id,
    tenant_id: plan.tenant_id,
    candidate_id: plan.candidate_id,
    followup_number: plan.followup_number,
    due_at: plan.due_at,
    sent_at: new Date(sentMs).toISOString(),
    provider_message_id: ids.messageId,
    provider_thread_id: ids.threadId,
    rationale_sha256: plan.rationale_sha256,
    subject_sha256: plan.subject_sha256,
    body_sha256: plan.body_sha256,
  });
}

module.exports = { sendGogFollowup, deliverFunderFollowup };
