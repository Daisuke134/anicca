"use strict";

const { createHash } = require("node:crypto");
const { buildFunderSubmissionReceipt } = require("./funder-submission-receipt.js");
const { isTrustedFunderGogThread } = require("./funder-gog-thread-reader.js");

const GMAIL_ID = /^[0-9a-f]{16,32}$/i;
const RESULT_STATUS = new Set(["reply_received", "rejected", "meeting_requested"]);
const WRAPPED = /^<<<EXTERNAL_UNTRUSTED_CONTENT id="[^"]+">>>\nSource: google_api\n---\n([\s\S]*)\n<<<END_EXTERNAL_UNTRUSTED_CONTENT id="[^"]+">>>$/;
const CONFIRMATION_BODY = "Your application to the Fall 2026 batch for Anicca has been submitted.";
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");
const NORMALIZED_MESSAGES = new WeakSet();
const VERIFIED_RESULTS = new WeakSet();

function fail() {
  throw new Error("funder thread result invalid");
}

function unwrap(value) {
  const text = String(value || "").trim();
  const match = WRAPPED.exec(text);
  return (match ? match[1] : text).trim();
}

function address(value) {
  const text = unwrap(value);
  const match = /<([^<>\s]+@[^<>\s]+)>/.exec(text) || /^([^<>\s]+@[^<>\s]+)$/.exec(text);
  if (!match) fail();
  return match[1].toLowerCase();
}

function verifiedReceipt(receipt) {
  if (!receipt || receipt.schema_version !== 1) fail();
  try {
    const rebuilt = buildFunderSubmissionReceipt({
      tenantId: receipt.tenant_id, funderId: receipt.funder_id,
      draftId: receipt.draft_id, applicationUrl: receipt.application_url,
      home: { status: receipt.provider_status, observedAt: receipt.home_observed_at },
      mail: {
        messageId: receipt.mail_message_id, threadId: receipt.mail_thread_id,
        internalDateMs: Date.parse(receipt.submitted_at), from: receipt.mail_sender,
        subject: receipt.mail_subject, body: CONFIRMATION_BODY,
        dkimPass: receipt.mail_auth && receipt.mail_auth.dkim,
        spfPass: receipt.mail_auth && receipt.mail_auth.spf,
        dmarcPass: receipt.mail_auth && receipt.mail_auth.dmarc,
      },
    });
    if (rebuilt.ledger_id !== receipt.ledger_id
      || rebuilt.evidence_digest !== receipt.evidence_digest) fail();
    return rebuilt;
  } catch { fail(); }
}

function normalizeMessage(raw, threadId) {
  const id = String(raw && raw.id || "").toLowerCase();
  const messageThread = String(raw && raw.threadId || "").toLowerCase();
  const internalDate = Number(raw && raw.internalDate);
  const headers = raw && raw.headers;
  const subject = unwrap(headers && headers.subject);
  const sender = address(headers && headers.from);
  const body = unwrap(raw && raw.body);
  if (!GMAIL_ID.test(id) || messageThread !== threadId
    || !Number.isSafeInteger(internalDate) || !subject || subject.length > 1000
    || !body || body.length > 100_000) fail();
  const message = Object.freeze({
    provider_message_id: id, provider_thread_id: messageThread,
    observed_at: new Date(internalDate).toISOString(), sender, subject, body,
  });
  NORMALIZED_MESSAGES.add(message);
  return message;
}

function normalizeFunderApplicationThread(raw, options = {}) {
  const receipt = verifiedReceipt(options.submissionReceipt);
  const ownerEmail = String(options.ownerEmail || "").trim().toLowerCase();
  const thread = raw && raw.thread;
  const threadId = String(thread && thread.id || "").toLowerCase();
  if (!isTrustedFunderGogThread(raw) || !ownerEmail.includes("@")
    || threadId !== receipt.mail_thread_id
    || !Array.isArray(thread.messages) || thread.messages.length < 1
    || thread.messages.length > 100) fail();
  const seen = new Set();
  const messages = thread.messages.map((rawMessage) => {
    const message = normalizeMessage(rawMessage, threadId);
    if (seen.has(message.provider_message_id)) fail();
    seen.add(message.provider_message_id);
    return message;
  });
  const confirmation = messages.find((message) =>
    message.provider_message_id === receipt.mail_message_id);
  if (!confirmation || confirmation.observed_at !== receipt.submitted_at
    || confirmation.sender !== receipt.mail_sender
    || confirmation.subject !== receipt.mail_subject) fail();
  const submittedMs = Date.parse(receipt.submitted_at);
  const replies = [];
  for (const message of messages) {
    if (message === confirmation) continue;
    const observedMs = Date.parse(message.observed_at);
    if (observedMs <= submittedMs) fail();
    if (message.sender === ownerEmail) continue;
    replies.push(message);
  }
  replies.sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at)
    || a.provider_message_id.localeCompare(b.provider_message_id));
  return Object.freeze({ confirmation, replies: Object.freeze(replies) });
}

function resultBase(receipt, message, resultType, status, evidenceSha, rationaleSha) {
  const source = verifiedReceipt(receipt);
  if (!message || !NORMALIZED_MESSAGES.has(message)
    || message.provider_thread_id !== source.mail_thread_id
    || !GMAIL_ID.test(String(message.provider_message_id || ""))
    || !Number.isFinite(Date.parse(message.observed_at))) fail();
  const fields = {
    schema_version: 1, tenant_id: source.tenant_id, organ: "fundraising",
    workflow: "funder_application", source_kind: "funder_submission",
    source_id: source.ledger_id, source_fence: 1, entity_id: source.funder_id,
    result_type: resultType, status,
    provider_message_id: message.provider_message_id,
    provider_thread_id: message.provider_thread_id, occurred_at: message.observed_at,
    sender_sha256: sha(message.sender), subject_sha256: sha(message.subject),
    body_sha256: sha(message.body),
    message_sha256: sha(JSON.stringify([message.provider_message_id,
      message.provider_thread_id, message.observed_at, message.sender,
      message.subject, message.body])),
    evidence_sha256: evidenceSha, rationale_sha256: rationaleSha,
  };
  const identity = JSON.stringify(fields);
  const result = Object.freeze({
    ...fields, result_id: `outbound-result:${sha(identity)}`,
  });
  VERIFIED_RESULTS.add(result);
  return result;
}

function buildFunderConfirmationResult(input = {}) {
  const receipt = verifiedReceipt(input.submissionReceipt);
  const message = input.message;
  if (!message || !NORMALIZED_MESSAGES.has(message)
    || message.provider_message_id !== receipt.mail_message_id
    || message.observed_at !== receipt.submitted_at
    || message.sender !== receipt.mail_sender || message.subject !== receipt.mail_subject) fail();
  return resultBase(receipt, message, "confirmation", "confirmed",
    receipt.evidence_digest, sha("verified_funder_submission_receipt"));
}

function buildFunderReplyResult(input = {}) {
  const receipt = verifiedReceipt(input.submissionReceipt);
  const message = input.message;
  const judgment = input.judgment;
  if (!message || !NORMALIZED_MESSAGES.has(message)
    || message.provider_message_id === receipt.mail_message_id
    || Date.parse(message.observed_at) <= Date.parse(receipt.submitted_at)
    || !judgment || judgment.kind !== "agent_judgment"
    || !RESULT_STATUS.has(judgment.status)) fail();
  const rationale = String(judgment.rationale || "").trim();
  const quotes = judgment.evidence_quotes;
  if (!rationale || rationale.length > 2000 || !Array.isArray(quotes)
    || quotes.length < 1 || quotes.length > 3) fail();
  const normalizedQuotes = quotes.map((quote) => String(quote || "").trim());
  if (normalizedQuotes.some((quote) => quote.length < 3 || quote.length > 500
    || !message.body.includes(quote))) fail();
  return resultBase(receipt, message, "reply", judgment.status,
    sha(normalizedQuotes.join("\n")), sha(rationale));
}

function isVerifiedFunderOutboundResult(value) {
  return !!(value && typeof value === "object" && VERIFIED_RESULTS.has(value));
}

module.exports = {
  normalizeFunderApplicationThread,
  buildFunderConfirmationResult,
  buildFunderReplyResult,
  isVerifiedFunderOutboundResult,
};
