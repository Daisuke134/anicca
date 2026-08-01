"use strict";

const DIGEST = /^[0-9a-f]{64}$/;

function valid(receipt) {
  return receipt && receipt.schema_version === 1
    && /^funder-outreach:[0-9a-f]{64}$/.test(String(receipt.outreach_id || ""))
    && /^funder-outreach-batch:[0-9a-f]{64}$/.test(String(receipt.batch_id || ""))
    && typeof receipt.tenant_id === "string" && receipt.tenant_id.length > 0
    && /^\d{4}-\d{2}-\d{2}$/.test(String(receipt.tokyo_date || ""))
    && typeof receipt.candidate_id === "string" && receipt.candidate_id.length > 1
    && typeof receipt.funder_name === "string" && receipt.funder_name.length > 0
    && [receipt.recipient_sha256, receipt.source_digest, receipt.fit_summary_sha256,
      receipt.subject_sha256, receipt.body_sha256].every((value) => DIGEST.test(String(value || "")))
    && /^https:\/\/[^\s]+$/.test(String(receipt.source_url || ""))
    && Number.isFinite(Date.parse(receipt.source_observed_at))
    && Number.isFinite(Date.parse(receipt.sent_at))
    && /^[0-9a-f]{16,32}$/i.test(String(receipt.provider_message_id || ""))
    && /^[0-9a-f]{16,32}$/i.test(String(receipt.provider_thread_id || ""));
}

async function appendFunderOutreachReceipt(receipt, options = {}) {
  if (!valid(receipt) || typeof options.query !== "function") throw new Error("funder outreach store invalid");
  const values = [
    receipt.tenant_id, receipt.outreach_id, receipt.batch_id, receipt.tokyo_date,
    receipt.candidate_id, receipt.funder_name, receipt.recipient_sha256,
    receipt.source_url, receipt.source_observed_at, receipt.source_digest,
    receipt.fit_summary_sha256, receipt.subject_sha256, receipt.body_sha256,
    receipt.sent_at, receipt.provider_message_id, receipt.provider_thread_id,
  ];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_outreach_ledger (
        tenant_id, outreach_id, batch_id, tokyo_date, candidate_id, funder_name,
        recipient_sha256, source_url, source_observed_at, source_digest,
        fit_summary_sha256, subject_sha256, body_sha256, sent_at,
        provider_message_id, provider_thread_id
      ) VALUES ($1,$2,$3,$4::date,$5,$6,$7,$8,$9::timestamptz,$10,$11,$12,$13,$14::timestamptz,$15,$16)
      ON CONFLICT DO NOTHING
      RETURNING outreach_id, true AS inserted
    ), replay AS (
      SELECT outreach_id, false AS inserted
      FROM public.lm_funder_outreach_ledger
      WHERE tenant_id=$1 AND outreach_id=$2 AND batch_id=$3 AND tokyo_date=$4::date
        AND candidate_id=$5 AND funder_name=$6 AND recipient_sha256=$7
        AND source_url=$8 AND source_observed_at=$9::timestamptz AND source_digest=$10
        AND fit_summary_sha256=$11 AND subject_sha256=$12 AND body_sha256=$13
        AND sent_at=$14::timestamptz AND provider_message_id=$15 AND provider_thread_id=$16
    )
    SELECT * FROM inserted
    UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, values);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("funder outreach store conflict");
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendFunderOutreachReceipt };
