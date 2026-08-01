"use strict";

const { createHash } = require("node:crypto");
const { buildFunderSubmissionReceipt } = require("./funder-submission-receipt.js");
const { notifyOpenClaw, parseOpenClawMessageId } = require("./outbound-guardian.js");
const { hashChatId } = require("./telegram.js");

function validate(receipt) {
  if (!receipt) throw new Error("funder submission Telegram receipt invalid");
  const rebuilt = buildFunderSubmissionReceipt({
    tenantId: receipt.tenant_id, funderId: receipt.funder_id,
    draftId: receipt.draft_id, applicationUrl: receipt.application_url,
    home: { status: receipt.provider_status, observedAt: receipt.home_observed_at },
    mail: {
      messageId: receipt.mail_message_id, threadId: receipt.mail_thread_id,
      internalDateMs: Date.parse(receipt.submitted_at), from: receipt.mail_sender,
      subject: receipt.mail_subject,
      body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
      dkimPass: receipt.mail_auth && receipt.mail_auth.dkim,
      spfPass: receipt.mail_auth && receipt.mail_auth.spf,
      dmarcPass: receipt.mail_auth && receipt.mail_auth.dmarc,
    },
  });
  if (rebuilt.ledger_id !== receipt.ledger_id) throw new Error("funder submission Telegram receipt invalid");
}

function buildFunderSubmissionMessage(receipt) {
  validate(receipt);
  const draft = `${receipt.draft_id.slice(0, 8)}…${receipt.draft_id.slice(-4)}`;
  return [
    "🚀 YC Fall 2026へ提出完了",
    "Anicca",
    "状態: 審査中（In review）",
    "確認メール: 受信・認証済み",
    `Application ID: ${draft}`,
    "Life Managerが返信・面談を追跡します。",
  ].join("\n");
}

function providerId(response) {
  try { return parseOpenClawMessageId(response); } catch {
    const match = typeof response === "string" && /message_id\s*:\s*([1-9]\d*)/i.exec(response);
    if (match) return match[1];
    throw new Error("Telegram delivery needs a positive message ID");
  }
}

async function deliverFunderSubmissionMessage(input = {}, dependencies = {}) {
  const tenant = String(input.tenantId || "").trim();
  const target = String(input.telegramTarget || "").trim();
  if (!/^[a-z0-9][a-z0-9._-]{0,127}$/i.test(tenant) || !target || target.length > 200) {
    throw new Error("funder submission Telegram delivery invalid");
  }
  const message = buildFunderSubmissionMessage(input.receipt);
  const response = await (dependencies.send || notifyOpenClaw)(message, { telegramTarget: target });
  const observedMs = Date.parse(String((dependencies.observedAt || (() => new Date().toISOString()))()));
  if (!Number.isFinite(observedMs)) throw new Error("funder submission Telegram observed time invalid");
  return Object.freeze({
    kind: "funder_submission_telegram_delivery",
    provider_id: providerId(response),
    observed_at: new Date(observedMs).toISOString(),
    tenant_id: tenant,
    chat_id_sha256: hashChatId(target),
    message_sha256: createHash("sha256").update(message, "utf8").digest("hex"),
    ledger_id: input.receipt.ledger_id,
  });
}

module.exports = { buildFunderSubmissionMessage, deliverFunderSubmissionMessage };
