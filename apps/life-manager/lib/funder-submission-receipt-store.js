"use strict";

const { buildFunderSubmissionReceipt } = require("./funder-submission-receipt.js");

function valid(receipt) {
  if (!receipt || receipt.schema_version !== 1) return false;
  try {
    const rebuilt = buildFunderSubmissionReceipt({
      tenantId: receipt.tenant_id,
      funderId: receipt.funder_id,
      draftId: receipt.draft_id,
      applicationUrl: receipt.application_url,
      home: { status: receipt.provider_status, observedAt: receipt.home_observed_at },
      mail: {
        messageId: receipt.mail_message_id,
        threadId: receipt.mail_thread_id,
        internalDateMs: Date.parse(receipt.submitted_at),
        from: receipt.mail_sender,
        subject: receipt.mail_subject,
        body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
        dkimPass: receipt.mail_auth && receipt.mail_auth.dkim,
        spfPass: receipt.mail_auth && receipt.mail_auth.spf,
        dmarcPass: receipt.mail_auth && receipt.mail_auth.dmarc,
      },
    });
    return rebuilt.ledger_id === receipt.ledger_id && rebuilt.evidence_digest === receipt.evidence_digest;
  } catch { return false; }
}

async function appendFunderSubmissionReceipt(receipt, options = {}) {
  if (!valid(receipt) || typeof options.query !== "function") throw new Error("funder submission receipt store invalid");
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_submission_ledger (
        tenant_id, ledger_id, funder_id, draft_id, application_url,
        status, provider_status, submitted_at, home_observed_at,
        mail_message_id, mail_thread_id, mail_sender, mail_subject,
        mail_auth, evidence_digest
      ) VALUES ($1, $2, $3, $4::uuid, $5, $6, $7, $8::timestamptz,
        $9::timestamptz, $10, $11, $12, $13, $14::jsonb, $15)
      ON CONFLICT DO NOTHING
      RETURNING ledger_id, true AS inserted
    ), replay AS (
      SELECT ledger_id, false AS inserted
      FROM public.lm_funder_submission_ledger
      WHERE tenant_id = $1 AND ledger_id = $2 AND funder_id = $3
        AND draft_id = $4::uuid AND application_url = $5 AND status = $6
        AND provider_status = $7 AND submitted_at = $8::timestamptz
        AND home_observed_at = $9::timestamptz AND mail_message_id = $10
        AND mail_thread_id = $11 AND mail_sender = $12 AND mail_subject = $13
        AND mail_auth = $14::jsonb AND evidence_digest = $15
    )
    SELECT * FROM inserted
    UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, [
    receipt.tenant_id, receipt.ledger_id, receipt.funder_id, receipt.draft_id,
    receipt.application_url, receipt.status, receipt.provider_status,
    receipt.submitted_at, receipt.home_observed_at, receipt.mail_message_id,
    receipt.mail_thread_id, receipt.mail_sender, receipt.mail_subject,
    JSON.stringify(receipt.mail_auth), receipt.evidence_digest,
  ]);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
    throw new Error("funder submission receipt store conflict");
  }
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendFunderSubmissionReceipt };
