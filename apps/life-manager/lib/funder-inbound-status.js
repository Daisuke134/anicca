"use strict";

const { createHash } = require("node:crypto");

const HEX_ID = /^[0-9a-f]{16,32}$/i;
const OUTREACH_ID = /^funder-outreach:[0-9a-f]{64}$/;
const ALLOWED = new Set([
  "delivery_failed",
  "reply_received",
  "rejected",
  "meeting_requested",
]);
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");

function fail() {
  throw new Error("funder inbound status invalid");
}

function address(value) {
  const text = String(value || "").trim();
  const match = /<([^<>\s]+@[^<>\s]+)>/.exec(text) || /^([^<>\s]+@[^<>\s]+)$/.exec(text);
  if (!match) fail();
  return match[1].toLowerCase();
}

function validateOutreach(receipt) {
  if (!receipt || receipt.schema_version !== 1
    || !String(receipt.tenant_id || "").trim()
    || !OUTREACH_ID.test(String(receipt.outreach_id || ""))
    || !String(receipt.candidate_id || "").trim()
    || !HEX_ID.test(String(receipt.provider_message_id || ""))
    || !HEX_ID.test(String(receipt.provider_thread_id || ""))
    || !Number.isFinite(Date.parse(receipt.sent_at))) fail();
}

function normalizeFunderInboundMessage(raw, options = {}) {
  const outreach = options.outreachReceipt;
  const owner = String(options.ownerEmail || "").trim().toLowerCase();
  validateOutreach(outreach);
  const headers = raw && raw.headers;
  const id = String(raw && raw.id || "").toLowerCase();
  const threadId = String(raw && raw.threadId || "").toLowerCase();
  const internalMs = Number(raw && raw.internalDate);
  const body = String(raw && raw.body || "").trim();
  const subject = String(headers && headers.subject || "").trim();
  const sender = address(headers && headers.from);
  if (!owner.includes("@") || sender === owner || !HEX_ID.test(id)
    || threadId !== String(outreach.provider_thread_id).toLowerCase()
    || !Number.isSafeInteger(internalMs) || internalMs < Date.parse(outreach.sent_at)
    || !body || body.length > 100_000 || !subject || subject.length > 1000) fail();
  return Object.freeze({
    provider_message_id: id,
    provider_thread_id: threadId,
    observed_at: new Date(internalMs).toISOString(),
    sender,
    subject,
    body,
  });
}

function classifyFunderInbound(input = {}) {
  const outreach = input.outreachReceipt;
  const message = input.message;
  const judgment = input.judgment;
  validateOutreach(outreach);
  if (!message || message.provider_thread_id !== String(outreach.provider_thread_id).toLowerCase()
    || !HEX_ID.test(String(message.provider_message_id || ""))
    || !Number.isFinite(Date.parse(message.observed_at))
    || typeof message.sender !== "string" || typeof message.subject !== "string"
    || typeof message.body !== "string" || !judgment || judgment.kind !== "agent_judgment"
    || !ALLOWED.has(judgment.status)) fail();
  const rationale = String(judgment.rationale || "").trim();
  const quotes = judgment.evidence_quotes;
  if (!rationale || rationale.length > 2000 || !Array.isArray(quotes)
    || quotes.length < 1 || quotes.length > 3) fail();
  const normalizedQuotes = quotes.map((quote) => String(quote || "").trim());
  if (normalizedQuotes.some((quote) => quote.length < 3 || quote.length > 500 || !message.body.includes(quote))) fail();

  const senderHash = sha(message.sender);
  const subjectHash = sha(message.subject);
  const bodyHash = sha(message.body);
  const evidenceHash = sha(normalizedQuotes.join("\n"));
  const rationaleHash = sha(rationale);
  const seed = [outreach.tenant_id, outreach.outreach_id, message.provider_message_id,
    judgment.status, evidenceHash, rationaleHash].join("\n");
  return Object.freeze({
    schema_version: 1,
    observation_id: `funder-inbound-status:${sha(seed)}`,
    tenant_id: outreach.tenant_id,
    outreach_id: outreach.outreach_id,
    candidate_id: outreach.candidate_id,
    status: judgment.status,
    provider_message_id: message.provider_message_id,
    provider_thread_id: message.provider_thread_id,
    observed_at: message.observed_at,
    sender_sha256: senderHash,
    subject_sha256: subjectHash,
    body_sha256: bodyHash,
    evidence_sha256: evidenceHash,
    rationale_sha256: rationaleHash,
  });
}

module.exports = { normalizeFunderInboundMessage, classifyFunderInbound };
