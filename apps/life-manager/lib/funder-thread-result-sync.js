"use strict";

const {
  normalizeFunderApplicationThread,
  buildFunderConfirmationResult,
  buildFunderReplyResult,
} = require("./funder-thread-result.js");
const { buildFunderSubmissionReceipt } = require("./funder-submission-receipt.js");

async function loadFunderSubmissionReceipt(input = {}) {
  const tenantId = String(input.tenantId || "");
  const sourceId = String(input.sourceId || "");
  if (!tenantId || !/^funder-ledger:[0-9a-f]{64}$/.test(sourceId)
    || typeof input.query !== "function") {
    throw new Error("funder thread sync source invalid");
  }
  const result = await input.query(`
    SELECT tenant_id,ledger_id,funder_id,draft_id::text,application_url,status,
      provider_status,submitted_at,home_observed_at,mail_message_id,mail_thread_id,
      mail_sender,mail_subject,mail_auth,evidence_digest
    FROM public.lm_funder_submission_ledger
    WHERE tenant_id=$1 AND ledger_id=$2
  `, [tenantId, sourceId]);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
    throw new Error("funder thread sync source conflict");
  }
  const row = result.rows[0];
  const receipt = buildFunderSubmissionReceipt({
    tenantId: row.tenant_id, funderId: row.funder_id, draftId: row.draft_id,
    applicationUrl: row.application_url,
    home: { status: row.provider_status,
      observedAt: new Date(row.home_observed_at).toISOString() },
    mail: {
      messageId: row.mail_message_id, threadId: row.mail_thread_id,
      internalDateMs: new Date(row.submitted_at).getTime(), from: row.mail_sender,
      subject: row.mail_subject,
      body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
      dkimPass: row.mail_auth && row.mail_auth.dkim,
      spfPass: row.mail_auth && row.mail_auth.spf,
      dmarcPass: row.mail_auth && row.mail_auth.dmarc,
    },
  });
  if (row.status !== receipt.status || row.ledger_id !== receipt.ledger_id
    || row.evidence_digest !== receipt.evidence_digest) {
    throw new Error("funder thread sync source conflict");
  }
  return receipt;
}

async function syncFunderThreadResults(input = {}) {
  const receipt = input.submissionReceipt;
  if (!input.reader || typeof input.reader.getThread !== "function"
    || typeof input.append !== "function") {
    throw new Error("funder thread result sync invalid");
  }
  const raw = await input.reader.getThread(receipt && receipt.mail_thread_id);
  const normalized = normalizeFunderApplicationThread(raw, {
    submissionReceipt: receipt, ownerEmail: input.ownerEmail,
  });
  const results = [];
  const confirmation = buildFunderConfirmationResult({
    submissionReceipt: receipt, message: normalized.confirmation,
  });
  const confirmationSave = await input.append(confirmation);
  results.push(Object.freeze({
    result_id: confirmation.result_id, result_type: confirmation.result_type,
    status: confirmation.status, provider_message_id: confirmation.provider_message_id,
    inserted: confirmationSave.inserted === true,
  }));
  const pending = [];
  const judgments = input.judgments && typeof input.judgments === "object"
    ? input.judgments : {};
  const replyIds = new Set(normalized.replies.map((message) => message.provider_message_id));
  if (Object.keys(judgments).some((messageId) => !replyIds.has(messageId))) {
    throw new Error("funder thread result sync contains unused judgment");
  }
  for (const message of normalized.replies) {
    const judgment = judgments[message.provider_message_id];
    if (!judgment) {
      pending.push(message.provider_message_id);
      continue;
    }
    const entry = buildFunderReplyResult({
      submissionReceipt: receipt, message, judgment,
    });
    const saved = await input.append(entry);
    results.push(Object.freeze({
      result_id: entry.result_id, result_type: entry.result_type,
      status: entry.status, provider_message_id: entry.provider_message_id,
      inserted: saved.inserted === true,
    }));
  }
  return Object.freeze({
    schema_version: 1, source_id: receipt.ledger_id,
    provider_thread_id: receipt.mail_thread_id,
    results: Object.freeze(results),
    pending_judgment_message_ids: Object.freeze(pending),
  });
}

module.exports = { syncFunderThreadResults, loadFunderSubmissionReceipt };
