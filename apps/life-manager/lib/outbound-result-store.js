"use strict";

const { createHash } = require("node:crypto");
const { isVerifiedFunderOutboundResult } = require("./funder-thread-result.js");
const { isVerifiedJobHunterOutboundResult } = require("./job-hunter-outbound-result.js");
const DIGEST = /^[0-9a-f]{64}$/;
const RESULT_ID = /^outbound-result:[0-9a-f]{64}$/;
const GMAIL_ID = /^[0-9a-f]{16,32}$/i;
const STATUSES = new Set(["confirmed", "reply_received", "rejected", "meeting_requested"]);
const FIELDS = Object.freeze([
  "schema_version", "tenant_id", "organ", "workflow", "source_kind", "source_id",
  "source_fence", "entity_id", "result_type", "status", "provider_message_id",
  "provider_thread_id", "occurred_at", "sender_sha256", "subject_sha256",
  "body_sha256", "message_sha256", "evidence_sha256", "rationale_sha256",
]);
const ALLOWED_KEYS = new Set([...FIELDS, "result_id"]);

function expectedResultId(value) {
  const identity = {};
  for (const field of FIELDS) identity[field] = value[field];
  const digest = createHash("sha256").update(JSON.stringify(identity), "utf8").digest("hex");
  return `outbound-result:${digest}`;
}

function valid(value) {
  return value && value.schema_version === 1 && RESULT_ID.test(String(value.result_id || ""))
    && Object.keys(value).length === ALLOWED_KEYS.size
    && Object.keys(value).every((key) => ALLOWED_KEYS.has(key))
    && value.result_id === expectedResultId(value)
    && String(value.tenant_id || "")
    && ((value.organ === "fundraising" && value.workflow === "funder_application"
      && value.source_kind === "funder_submission"
      && /^funder-ledger:[0-9a-f]{64}$/.test(String(value.source_id || ""))
      && value.source_fence === 1 && value.entity_id === "yc-fall-2026"
      && [value.sender_sha256, value.subject_sha256, value.body_sha256]
        .every((field) => DIGEST.test(String(field || ""))))
      || (value.organ === "job_hunter" && value.workflow === "job_application"
        && value.source_kind === "job_submit_intent"
        && /^job-intent:[0-9a-f]{32}$/.test(String(value.source_id || ""))
        && Number.isSafeInteger(value.source_fence) && value.source_fence >= 1
        && /^[0-9a-f]{64}$/.test(String(value.entity_id || ""))
        && value.sender_sha256 === null && value.subject_sha256 === null
        && value.body_sha256 === null))
    && ((value.result_type === "confirmation" && value.status === "confirmed")
      || (value.result_type === "reply" && STATUSES.has(value.status) && value.status !== "confirmed"))
    && GMAIL_ID.test(String(value.provider_message_id || ""))
    && GMAIL_ID.test(String(value.provider_thread_id || ""))
    && Number.isFinite(Date.parse(value.occurred_at))
    && [value.message_sha256, value.evidence_sha256, value.rationale_sha256]
      .every((field) => DIGEST.test(String(field || "")));
}

async function appendOutboundResult(value, options = {}) {
  const provenance = value && value.organ === "job_hunter"
    ? isVerifiedJobHunterOutboundResult(value)
    : isVerifiedFunderOutboundResult(value);
  if (!provenance || !valid(value) || typeof options.query !== "function") {
    throw new Error("outbound result store invalid");
  }
  const params = [value.tenant_id, value.result_id, value.organ, value.workflow,
    value.source_kind, value.source_id, value.source_fence, value.entity_id,
    value.result_type, value.status, value.provider_message_id,
    value.provider_thread_id, value.occurred_at, value.sender_sha256,
    value.subject_sha256, value.body_sha256, value.message_sha256,
    value.evidence_sha256, value.rationale_sha256];
  if (value.organ === "job_hunter") {
    if (typeof options.verifyJobHunterSource !== "function"
      || await options.verifyJobHunterSource(value) !== true) {
      throw new Error("outbound result store source verification failed");
    }
    const result = await options.query(`
      WITH inserted AS (
        INSERT INTO public.lm_outbound_result_ledger (
          tenant_id,result_id,organ,workflow,source_kind,source_id,source_fence,
          entity_id,result_type,status,provider_message_id,provider_thread_id,
          occurred_at,sender_sha256,subject_sha256,body_sha256,message_sha256,
          evidence_sha256,rationale_sha256
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::timestamptz,
          $14,$15,$16,$17,$18,$19)
        ON CONFLICT DO NOTHING RETURNING result_id,true AS inserted
      ), replay AS (
        SELECT result_id,false AS inserted FROM public.lm_outbound_result_ledger
        WHERE tenant_id=$1 AND result_id=$2 AND organ=$3 AND workflow=$4
          AND source_kind=$5 AND source_id=$6 AND source_fence=$7 AND entity_id=$8
          AND result_type=$9 AND status=$10 AND provider_message_id=$11
          AND provider_thread_id=$12 AND occurred_at=$13::timestamptz
          AND sender_sha256 IS NOT DISTINCT FROM $14
          AND subject_sha256 IS NOT DISTINCT FROM $15
          AND body_sha256 IS NOT DISTINCT FROM $16
          AND message_sha256=$17 AND evidence_sha256=$18 AND rationale_sha256=$19
      )
      SELECT * FROM inserted UNION ALL
      SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
    `, params);
    if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
      throw new Error("outbound result store conflict");
    }
    return Object.freeze({ ...result.rows[0] });
  }
  const result = await options.query(`
    WITH source AS (
      SELECT source.tenant_id
      FROM public.lm_funder_submission_ledger AS source
      WHERE source.tenant_id=$1 AND source.ledger_id=$6 AND source.funder_id=$8
        AND source.mail_thread_id=$12 AND source.submitted_at <= $13::timestamptz
        AND (($9='confirmation' AND source.mail_message_id=$11
              AND source.submitted_at=$13::timestamptz)
          OR ($9='reply' AND source.mail_message_id<>$11))
    ), inserted AS (
      INSERT INTO public.lm_outbound_result_ledger (
        tenant_id,result_id,organ,workflow,source_kind,source_id,source_fence,
        entity_id,result_type,status,provider_message_id,provider_thread_id,
        occurred_at,sender_sha256,subject_sha256,body_sha256,message_sha256,
        evidence_sha256,rationale_sha256
      ) SELECT $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::timestamptz,
        $14,$15,$16,$17,$18,$19 FROM source
      ON CONFLICT DO NOTHING RETURNING result_id,true AS inserted
    ), replay AS (
      SELECT result_id,false AS inserted
      FROM public.lm_outbound_result_ledger
      WHERE tenant_id=$1 AND result_id=$2 AND organ=$3 AND workflow=$4
        AND source_kind=$5 AND source_id=$6 AND source_fence=$7 AND entity_id=$8
        AND result_type=$9 AND status=$10 AND provider_message_id=$11
        AND provider_thread_id=$12 AND occurred_at=$13::timestamptz
        AND sender_sha256=$14 AND subject_sha256=$15 AND body_sha256=$16
        AND message_sha256=$17 AND evidence_sha256=$18 AND rationale_sha256=$19
    )
    SELECT * FROM inserted UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, params);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) {
    throw new Error("outbound result store conflict");
  }
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendOutboundResult };
