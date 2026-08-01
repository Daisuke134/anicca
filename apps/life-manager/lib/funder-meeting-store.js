"use strict";

const DIGEST = /^[0-9a-f]{64}$/;
const HEX_ID = /^[0-9a-f]{16,32}$/i;

function valid(value) {
  return value && value.schema_version === 1
    && /^funder-meeting:[0-9a-f]{64}$/.test(String(value.meeting_id || ""))
    && /^funder-outreach:[0-9a-f]{64}$/.test(String(value.outreach_id || ""))
    && /^funder-inbound-status:[0-9a-f]{64}$/.test(String(value.status_observation_id || ""))
    && String(value.tenant_id || "") && String(value.candidate_id || "")
    && HEX_ID.test(String(value.provider_message_id || ""))
    && HEX_ID.test(String(value.provider_thread_id || ""))
    && Number.isFinite(Date.parse(value.scheduled_start_at))
    && Number.isFinite(Date.parse(value.scheduled_end_at))
    && Date.parse(value.scheduled_end_at) > Date.parse(value.scheduled_start_at)
    && String(value.provider_event_id || "").length > 0
    && /^https:\/\/calendar\.google\.com\//.test(String(value.provider_event_url || ""))
    && [value.schedule_evidence_sha256, value.schedule_rationale_sha256,
      value.brief_sha256, value.brief_rationale_sha256, value.kit_digest]
      .every((item) => DIGEST.test(String(item || "")))
    && Number.isFinite(Date.parse(value.recorded_at));
}

async function appendFunderMeetingReceipt(value, options = {}) {
  if (!valid(value) || typeof options.query !== "function") throw new Error("funder meeting store invalid");
  const params = [value.tenant_id, value.meeting_id, value.outreach_id, value.candidate_id,
    value.status_observation_id, value.provider_message_id, value.provider_thread_id,
    value.scheduled_start_at, value.scheduled_end_at, value.provider_event_id,
    value.provider_event_url, value.schedule_evidence_sha256, value.schedule_rationale_sha256,
    value.brief_sha256, value.brief_rationale_sha256, value.kit_digest, value.recorded_at];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_meeting_ledger (
        tenant_id, meeting_id, outreach_id, candidate_id, status_observation_id,
        provider_message_id, provider_thread_id, scheduled_start_at, scheduled_end_at,
        provider_event_id, provider_event_url, schedule_evidence_sha256,
        schedule_rationale_sha256, brief_sha256, brief_rationale_sha256,
        kit_digest, recorded_at
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::timestamptz,$9::timestamptz,$10,$11,$12,$13,$14,$15,$16,$17::timestamptz)
      ON CONFLICT DO NOTHING RETURNING meeting_id, true AS inserted
    ), replay AS (
      SELECT meeting_id, false AS inserted FROM public.lm_funder_meeting_ledger
      WHERE tenant_id=$1 AND meeting_id=$2 AND outreach_id=$3 AND candidate_id=$4
        AND status_observation_id=$5 AND provider_message_id=$6 AND provider_thread_id=$7
        AND scheduled_start_at=$8::timestamptz AND scheduled_end_at=$9::timestamptz
        AND provider_event_id=$10 AND provider_event_url=$11
        AND schedule_evidence_sha256=$12 AND schedule_rationale_sha256=$13
        AND brief_sha256=$14 AND brief_rationale_sha256=$15 AND kit_digest=$16
        AND recorded_at=$17::timestamptz
    )
    SELECT * FROM inserted UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, params);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("funder meeting store conflict");
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendFunderMeetingReceipt };
