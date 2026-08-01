"use strict";

const {
  isVerifiedFunderWeeklyReflection,
  adoptPersistedFunderWeeklyReflection,
} = require("./funder-weekly-reflection.js");

function fail() { throw new Error("funder weekly reflection store invalid"); }

async function appendFunderWeeklyReflection(value, options = {}) {
  if (!isVerifiedFunderWeeklyReflection(value) || typeof options.query !== "function") fail();
  const params = [
    value.tenant_id, value.reflection_id, value.week_key, value.week_start, value.week_end,
    value.reflected_at, value.snapshot_digest, value.decision, value.reason,
    value.summary_sha256, value.rationale_sha256, JSON.stringify(value.outcome_result_ids),
    JSON.stringify(value.ranked_candidate_ids), JSON.stringify(value.pitch_directives),
  ];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_weekly_reflection_ledger (
        tenant_id, reflection_id, week_key, week_start, week_end, reflected_at,
        snapshot_digest, decision, reason, summary_sha256, rationale_sha256,
        outcome_result_ids, ranked_candidate_ids, pitch_directives
      ) VALUES ($1,$2,$3::date,$4::timestamptz,$5::timestamptz,$6::timestamptz,
        $7,$8,$9,$10,$11,$12::jsonb,$13::jsonb,$14::jsonb)
      ON CONFLICT DO NOTHING RETURNING reflection_id, true AS inserted
    ), replay AS (
      SELECT reflection_id, false AS inserted
      FROM public.lm_funder_weekly_reflection_ledger
      WHERE tenant_id=$1 AND reflection_id=$2 AND week_key=$3::date
        AND week_start=$4::timestamptz AND week_end=$5::timestamptz
        AND reflected_at=$6::timestamptz AND snapshot_digest=$7 AND decision=$8
        AND reason=$9 AND summary_sha256=$10 AND rationale_sha256=$11
        AND outcome_result_ids=$12::jsonb AND ranked_candidate_ids=$13::jsonb
        AND pitch_directives=$14::jsonb
    )
    SELECT * FROM inserted
    UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, params);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1
    || result.rows[0].reflection_id !== value.reflection_id) {
    throw new Error("funder weekly reflection store conflict");
  }
  return Object.freeze({
    reflection_id: result.rows[0].reflection_id,
    inserted: result.rows[0].inserted === true,
  });
}

function rowToPortable(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) fail();
  const copy = { ...row };
  for (const key of ["week_start", "week_end", "reflected_at"]) {
    if (copy[key] instanceof Date) copy[key] = copy[key].toISOString();
  }
  if (copy.week_key instanceof Date) copy.week_key = copy.week_key.toISOString().slice(0, 10);
  return copy;
}

async function loadLatestFunderWeeklyReflection(input = {}, options = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const beforeMs = Date.parse(String(input.before || ""));
  if (!tenantId || !Number.isFinite(beforeMs) || typeof options.query !== "function") fail();
  const result = await options.query(`
    SELECT 1 AS schema_version, tenant_id, reflection_id, week_key::text,
      week_start, week_end, reflected_at, snapshot_digest, decision, reason,
      summary_sha256, rationale_sha256, outcome_result_ids,
      ranked_candidate_ids, pitch_directives
    FROM public.lm_funder_weekly_reflection_ledger
    WHERE tenant_id=$1 AND reflected_at <= $2::timestamptz AND decision='change'
      AND NOT EXISTS (
        SELECT 1 FROM public.lm_funder_outreach_reflection_application applied
        WHERE applied.tenant_id=lm_funder_weekly_reflection_ledger.tenant_id
          AND applied.reflection_id=lm_funder_weekly_reflection_ledger.reflection_id
      )
    ORDER BY week_start DESC, reflection_id DESC
    LIMIT 1
  `, [tenantId, new Date(beforeMs).toISOString()]);
  if (!result || !Array.isArray(result.rows) || result.rows.length > 1) fail();
  if (result.rows.length === 0) return null;
  return adoptPersistedFunderWeeklyReflection(rowToPortable(result.rows[0]));
}

module.exports = { appendFunderWeeklyReflection, loadLatestFunderWeeklyReflection };
