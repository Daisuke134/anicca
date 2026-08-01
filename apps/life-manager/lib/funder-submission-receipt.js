"use strict";

const { createHash } = require("node:crypto");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const GMAIL_ID = /^[0-9a-f]{16}$/i;
const EXPECTED = Object.freeze({
  funderId: "yc-fall-2026",
  applicationUrl: "https://apply.ycombinator.com/home",
  homeStatus: "in_review",
  sender: "apply@ycombinator.com",
  subject: "YC Fall 2026 Application Submitted",
  body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
});

function fail() {
  throw new Error("submission receipt evidence invalid");
}

function digest(fields) {
  return createHash("sha256").update(JSON.stringify(fields), "utf8").digest("hex");
}

function buildFunderSubmissionReceipt(input = {}) {
  const home = input.home || {};
  const mail = input.mail || {};
  const mailMs = Number(mail.internalDateMs);
  const homeMs = Date.parse(String(home.observedAt || ""));
  if (
    !TENANT.test(String(input.tenantId || ""))
    || input.funderId !== EXPECTED.funderId
    || !UUID.test(String(input.draftId || ""))
    || input.applicationUrl !== EXPECTED.applicationUrl
    || home.status !== EXPECTED.homeStatus
    || !GMAIL_ID.test(String(mail.messageId || ""))
    || !GMAIL_ID.test(String(mail.threadId || ""))
    || mail.from !== EXPECTED.sender
    || mail.subject !== EXPECTED.subject
    || mail.body !== EXPECTED.body
    || mail.dkimPass !== true || mail.spfPass !== true || mail.dmarcPass !== true
    || !Number.isSafeInteger(mailMs) || !Number.isFinite(homeMs)
    || homeMs < mailMs || homeMs - mailMs > 10 * 60 * 1000
  ) fail();

  const evidence = Object.freeze({
    tenant_id: input.tenantId,
    funder_id: input.funderId,
    draft_id: input.draftId.toLowerCase(),
    application_url: input.applicationUrl,
    provider_status: home.status,
    submitted_at: new Date(mailMs).toISOString(),
    home_observed_at: new Date(homeMs).toISOString(),
    mail_message_id: mail.messageId.toLowerCase(),
    mail_thread_id: mail.threadId.toLowerCase(),
    mail_sender: mail.from,
    mail_subject: mail.subject,
    mail_auth: Object.freeze({ dkim: true, spf: true, dmarc: true }),
  });
  const evidenceDigest = digest(evidence);
  return Object.freeze({
    schema_version: 1,
    ledger_id: `funder-ledger:${evidenceDigest}`,
    status: "submitted",
    ...evidence,
    evidence_digest: evidenceDigest,
  });
}

module.exports = { buildFunderSubmissionReceipt };
