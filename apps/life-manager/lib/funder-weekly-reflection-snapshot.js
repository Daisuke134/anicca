"use strict";

const DIGEST = /^[0-9a-f]{64}$/;
const ID = /^[a-z0-9][a-z0-9._:-]{0,191}$/i;
const STATUS = new Set([
  "confirmed", "delivery_failed", "reply_received", "rejected", "meeting_requested", "offer_received", "funded",
]);

function fail() { throw new Error("funder weekly reflection snapshot invalid"); }
function iso(value) {
  const ms = Date.parse(String(value || ""));
  if (!Number.isFinite(ms)) fail();
  return new Date(ms).toISOString();
}

async function collectFunderWeeklyReflectionSnapshot(input = {}, options = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const start = iso(input.week_start);
  const end = iso(input.week_end);
  if (!tenantId || Date.parse(end) <= Date.parse(start) || typeof options.query !== "function") fail();
  const result = await options.query(`
    WITH exposure AS (
      SELECT ledger_id AS exposure_id,funder_id AS candidate_id,'submission'::text AS exposure_kind,
        submitted_at AS occurred_at,evidence_digest AS subject_sha256,evidence_digest AS body_sha256
      FROM public.lm_funder_submission_ledger WHERE tenant_id=$1 AND submitted_at < $3::timestamptz
      UNION ALL
      SELECT outreach_id,candidate_id,'outreach'::text,sent_at,subject_sha256,body_sha256
      FROM public.lm_funder_outreach_ledger WHERE tenant_id=$1 AND sent_at < $3::timestamptz
    ), result_row AS (
      SELECT result_id,source_id AS exposure_id,entity_id AS candidate_id,status,occurred_at AS observed_at
      FROM public.lm_outbound_result_ledger
      WHERE tenant_id=$1 AND organ='fundraising'
        AND occurred_at < $3::timestamptz
        AND (occurred_at >= $2::timestamptz OR (
          status IN ('reply_received','rejected','meeting_requested','offer_received','funded')
          AND NOT EXISTS (
            SELECT 1 FROM public.lm_funder_weekly_reflection_ledger reflected
            WHERE reflected.tenant_id=$1 AND reflected.outcome_result_ids ? result_id
          )
        ))
      UNION ALL
      SELECT observation_id,outreach_id,candidate_id,status,observed_at
      FROM public.lm_funder_inbound_status_ledger
      WHERE tenant_id=$1 AND observed_at < $3::timestamptz
        AND (observed_at >= $2::timestamptz OR (
          status IN ('reply_received','rejected','meeting_requested','offer_received','funded')
          AND NOT EXISTS (
            SELECT 1 FROM public.lm_funder_weekly_reflection_ledger reflected
            WHERE reflected.tenant_id=$1 AND reflected.outcome_result_ids ? observation_id
          )
        ))
    )
    SELECT 'exposure'::text AS record_kind,exposure_id,candidate_id,exposure_kind,
      occurred_at,subject_sha256,body_sha256,NULL::text AS result_id,
      NULL::text AS status,NULL::timestamptz AS observed_at
    FROM exposure
    UNION ALL
    SELECT 'result',exposure_id,candidate_id,NULL,NULL,NULL,NULL,result_id,status,observed_at
    FROM result_row
    ORDER BY record_kind,exposure_id,result_id
  `, [tenantId, start, end]);
  if (!result || !Array.isArray(result.rows) || result.rows.length > 20_000) fail();
  const exposures = [];
  const results = [];
  for (const row of result.rows) {
    if (row.record_kind === "exposure") {
      if (!ID.test(String(row.exposure_id || "")) || !ID.test(String(row.candidate_id || ""))
        || !new Set(["submission", "outreach"]).has(row.exposure_kind)
        || !DIGEST.test(String(row.subject_sha256 || "")) || !DIGEST.test(String(row.body_sha256 || ""))) fail();
      exposures.push({
        exposure_id: row.exposure_id,
        candidate_id: row.candidate_id,
        exposure_kind: row.exposure_kind,
        occurred_at: iso(row.occurred_at),
        subject_sha256: row.subject_sha256,
        body_sha256: row.body_sha256,
      });
    } else if (row.record_kind === "result") {
      if (!ID.test(String(row.result_id || "")) || !ID.test(String(row.candidate_id || ""))
        || !STATUS.has(row.status)) fail();
      const source = exposures.find((item) => item.candidate_id === row.candidate_id
        && item.exposure_id === row.exposure_id);
      // UNION result rows retain exposure_id in SQL; a missing or unbound source is never reflected.
      if (!source) fail();
      results.push({
        result_id: row.result_id,
        exposure_id: source.exposure_id,
        candidate_id: row.candidate_id,
        status: row.status,
        observed_at: iso(row.observed_at),
      });
    } else fail();
  }
  const supplied = input.candidateIds;
  const candidates = supplied === undefined
    ? []
    : [...supplied];
  if (candidates.some((id) => !ID.test(String(id || "")))
    || new Set(candidates).size !== candidates.length) fail();
  return Object.freeze({
    exposures: Object.freeze(exposures),
    results: Object.freeze(results),
    candidates: Object.freeze(candidates),
  });
}

module.exports = { collectFunderWeeklyReflectionSnapshot };
