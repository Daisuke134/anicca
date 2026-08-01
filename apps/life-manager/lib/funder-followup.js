"use strict";

const { createHash } = require("node:crypto");

const HEX_ID = /^[0-9a-f]{16,32}$/i;
const DIGEST = /^[0-9a-f]{64}$/;
const PLACEHOLDER = /\{\{|\}\}|TODO|TBD|<placeholder>/i;
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");

function fail() { throw new Error("funder follow-up invalid"); }

function header(message, name) {
  const headers = message && message.payload && message.payload.headers;
  if (!Array.isArray(headers)) fail();
  const matches = headers.filter((item) => String(item && item.name || "").toLowerCase() === name.toLowerCase());
  if (matches.length !== 1 || !String(matches[0].value || "").trim()) fail();
  return String(matches[0].value).trim();
}

function address(value) {
  const bracketed = /<([^<>\s]+@[^<>\s]+)>/.exec(value);
  const plain = /^([^<>\s]+@[^<>\s]+)$/.exec(value);
  const result = String(bracketed && bracketed[1] || plain && plain[1] || "").toLowerCase();
  if (!result) fail();
  return result;
}

function normalizeFunderThread(raw, options = {}) {
  const ownerEmail = String(options.ownerEmail || "").trim().toLowerCase();
  const expected = String(options.expectedThreadId || "").trim().toLowerCase();
  const thread = raw && raw.thread ? raw.thread : raw;
  if (!ownerEmail.includes("@") || !HEX_ID.test(expected) || !thread
    || String(thread.id || "").toLowerCase() !== expected || !Array.isArray(thread.messages) || thread.messages.length < 1) fail();
  const seen = new Set();
  const messages = thread.messages.map((message) => {
    const id = String(message && message.id || "").toLowerCase();
    const internalMs = Number(message && message.internalDate);
    const from = address(header(message, "From"));
    const subject = header(message, "Subject");
    if (!HEX_ID.test(id) || seen.has(id) || !Number.isSafeInteger(internalMs) || internalMs <= 0
      || !Array.isArray(message.labelIds)) fail();
    seen.add(id);
    return Object.freeze({
      message_id: id,
      internal_date: new Date(internalMs).toISOString(),
      direction: from === ownerEmail ? "outbound" : "inbound",
      from_sha256: sha(from),
      subject_sha256: sha(subject),
      labels: Object.freeze([...message.labelIds].map(String).sort()),
    });
  }).sort((a, b) => Date.parse(a.internal_date) - Date.parse(b.internal_date) || a.message_id.localeCompare(b.message_id));
  return Object.freeze({ thread_id: expected, owner_email_sha256: sha(ownerEmail), messages: Object.freeze(messages) });
}

function validateOutreach(receipt) {
  if (!receipt || receipt.schema_version !== 1
    || !/^funder-outreach:[0-9a-f]{64}$/.test(String(receipt.outreach_id || ""))
    || !/^funder-outreach-batch:[0-9a-f]{64}$/.test(String(receipt.batch_id || ""))
    || !String(receipt.tenant_id || "") || !String(receipt.candidate_id || "")
    || !DIGEST.test(String(receipt.recipient_sha256 || ""))
    || !HEX_ID.test(String(receipt.provider_message_id || ""))
    || !HEX_ID.test(String(receipt.provider_thread_id || ""))
    || !Number.isFinite(Date.parse(receipt.sent_at))) fail();
}

function validatePrior(prior, outreach, thread) {
  if (!Array.isArray(prior) || prior.length > 2) fail();
  const ordered = [...prior].sort((a, b) => a.followup_number - b.followup_number);
  for (let index = 0; index < ordered.length; index += 1) {
    const row = ordered[index];
    if (!row || row.schema_version !== 1 || row.followup_number !== index + 1
      || !/^funder-followup:[0-9a-f]{64}$/.test(String(row.followup_id || ""))
      || row.outreach_id !== outreach.outreach_id || row.batch_id !== outreach.batch_id
      || row.tenant_id !== outreach.tenant_id || row.candidate_id !== outreach.candidate_id
      || String(row.provider_thread_id).toLowerCase() !== String(outreach.provider_thread_id).toLowerCase()
      || !HEX_ID.test(String(row.provider_message_id || "")) || !Number.isFinite(Date.parse(row.sent_at))
      || ![row.rationale_sha256, row.subject_sha256, row.body_sha256].every((value) => DIGEST.test(String(value || "")))) fail();
    const observed = thread.messages.find((message) => message.message_id === String(row.provider_message_id).toLowerCase());
    if (!observed || observed.direction !== "outbound") fail();
  }
  return ordered;
}

function validateDraft(draft) {
  const subject = String(draft && draft.subject || "").trim();
  const body = String(draft && draft.body || "").trim();
  const rationale = String(draft && draft.rationale || "").trim();
  const words = body.split(/\s+/).filter(Boolean).length;
  if (!draft || draft.kind !== "agent_judgment" || !rationale || !subject || subject.length > 80
    || !body || words > 100 || PLACEHOLDER.test(subject) || PLACEHOLDER.test(body) || PLACEHOLDER.test(rationale)
    || !/https:\/\/aniccaai\.com(?:[\s/]|$)/i.test(body) || !/(15-minute|15 min|15分)/i.test(body)) fail();
  return { subject, body, rationale };
}

function planFunderFollowup(input = {}) {
  const outreach = input.outreachReceipt;
  const thread = input.thread;
  validateOutreach(outreach);
  if (!thread || String(thread.thread_id).toLowerCase() !== String(outreach.provider_thread_id).toLowerCase()
    || !Array.isArray(thread.messages)) fail();
  const initial = thread.messages.find((message) => message.message_id === String(outreach.provider_message_id).toLowerCase());
  if (!initial || initial.direction !== "outbound") fail();
  const prior = validatePrior(input.priorFollowups, outreach, thread);
  const inbound = thread.messages.find((message) => message.direction === "inbound" && Date.parse(message.internal_date) >= Date.parse(outreach.sent_at));
  if (inbound) return Object.freeze({
    status: "suppressed_inbound",
    outreach_id: outreach.outreach_id,
    provider_thread_id: outreach.provider_thread_id,
    inbound_message_id: inbound.message_id,
    inbound_observed_at: inbound.internal_date,
  });
  if (prior.length === 2) return Object.freeze({
    status: "complete",
    outreach_id: outreach.outreach_id,
    provider_thread_id: outreach.provider_thread_id,
    followup_count: 2,
  });
  const nowMs = Date.parse(String(input.now || ""));
  if (!Number.isFinite(nowMs)) fail();
  const number = prior.length + 1;
  const baseMs = Date.parse(prior.length === 0 ? outreach.sent_at : prior[0].sent_at);
  const delayMs = (prior.length === 0 ? 72 : 96) * 60 * 60 * 1000;
  const dueAt = new Date(baseMs + delayMs).toISOString();
  if (nowMs < Date.parse(dueAt)) return Object.freeze({
    status: "scheduled",
    followup_number: number,
    due_at: dueAt,
    outreach_id: outreach.outreach_id,
    provider_thread_id: outreach.provider_thread_id,
  });
  const draft = validateDraft(input.draft);
  const rationaleHash = sha(draft.rationale);
  const subjectHash = sha(draft.subject);
  const bodyHash = sha(draft.body);
  const replyTo = prior.length === 0 ? outreach.provider_message_id : prior.at(-1).provider_message_id;
  return Object.freeze({
    status: "due",
    followup_id: `funder-followup:${sha(`${outreach.outreach_id}\n${number}\n${dueAt}\n${rationaleHash}\n${subjectHash}\n${bodyHash}`)}`,
    outreach_id: outreach.outreach_id,
    batch_id: outreach.batch_id,
    tenant_id: outreach.tenant_id,
    candidate_id: outreach.candidate_id,
    followup_number: number,
    due_at: dueAt,
    provider_thread_id: outreach.provider_thread_id,
    reply_to_message_id: replyTo,
    rationale_sha256: rationaleHash,
    subject_sha256: subjectHash,
    body_sha256: bodyHash,
    subject: draft.subject,
    body: draft.body,
    thread_id: outreach.provider_thread_id,
  });
}

module.exports = { normalizeFunderThread, planFunderFollowup };
