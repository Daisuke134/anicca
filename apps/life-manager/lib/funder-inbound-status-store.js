"use strict";

const DIGEST = /^[0-9a-f]{64}$/;
const STATUS = new Set(["delivery_failed", "reply_received", "rejected", "meeting_requested"]);

function valid(value) {
  return value && value.schema_version === 1
    && /^funder-inbound-status:[0-9a-f]{64}$/.test(String(value.observation_id || ""))
    && /^funder-outreach:[0-9a-f]{64}$/.test(String(value.outreach_id || ""))
    && String(value.tenant_id || "") && String(value.candidate_id || "")
    && STATUS.has(value.status)
    && /^[0-9a-f]{16,32}$/i.test(String(value.provider_message_id || ""))
    && /^[0-9a-f]{16,32}$/i.test(String(value.provider_thread_id || ""))
    && Number.isFinite(Date.parse(value.observed_at))
    && [value.sender_sha256, value.subject_sha256, value.body_sha256,
      value.evidence_sha256, value.rationale_sha256].every((item) => DIGEST.test(String(item || "")));
}

async function appendFunderInboundStatus(value, options = {}) {
  if (!valid(value) || typeof options.query !== "function") {
    throw new Error("funder inbound status store invalid");
  }
  const params = [value.tenant_id, value.observation_id, value.outreach_id,
    value.candidate_id, value.status, value.provider_message_id, value.provider_thread_id,
    value.observed_at, value.sender_sha256, value.subject_sha256, value.body_sha256,
    value.evidence_sha256, value.rationale_sha256];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_inbound_status_ledger (
        tenant_id, observation_id, outreach_id, candidate_id, status,
        provider_message_id, provider_thread_id, observed_at, sender_sha256,
        subject_sha256, body_sha256, evidence_sha256, rationale_sha256
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::timestamptz,$9,$10,$11,$12,$13)
      ON CONFLICT DO NOTHING RETURNING observation_id, true AS inserted
    ), replay AS (
      SELECT observation_id, false AS inserted
      FROM public.lm_funder_inbound_status_ledger
      WHERE tenant_id=$1 AND observation_id=$2 AND outreach_id=$3 AND candidate_id=$4
        AND status=$5 AND provider_message_id=$6 AND provider_thread_id=$7
        AND observed_at=$8::timestamptz AND sender_sha256=$9 AND subject_sha256=$10
        AND body_sha256=$11 AND evidence_sha256=$12 AND rationale_sha256=$13
    )
    SELECT * FROM inserted UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, params);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
    throw new Error("funder inbound status store conflict");
  }
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendFunderInboundStatus };
