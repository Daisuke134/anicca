"use strict";

const { createHash } = require("node:crypto");

const DIGEST = /^[0-9a-f]{64}$/;
const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");

function decisionFields(input) {
  if (!input || !["scheduled", "suppressed_inbound", "complete"].includes(input.status)
    || !/^funder-outreach:[0-9a-f]{64}$/.test(String(input.outreach_id || ""))
    || !String(input.tenant_id || "") || !String(input.candidate_id || "")
    || !/^[0-9a-f]{16,32}$/i.test(String(input.provider_thread_id || ""))
    || !Number.isFinite(Date.parse(input.observed_at))) throw new Error("funder follow-up decision store invalid");
  const number = input.status === "scheduled" ? Number(input.followup_number) : null;
  const dueAt = input.status === "scheduled" ? String(input.due_at || "") : null;
  const inbound = input.status === "suppressed_inbound" ? String(input.inbound_message_id || "") : null;
  if ((input.status === "scheduled" && (![1, 2].includes(number) || !Number.isFinite(Date.parse(dueAt))))
    || (input.status === "suppressed_inbound" && !/^[0-9a-f]{16,32}$/i.test(inbound))
    || (input.status === "complete" && input.followup_count !== 2)) throw new Error("funder follow-up decision store invalid");
  const seed = [input.tenant_id, input.outreach_id, input.status, number || "", dueAt || "", inbound || "", input.observed_at].join("\n");
  return { decisionId: `funder-followup-decision:${sha(seed)}`, number, dueAt, inbound };
}

async function appendFunderFollowupDecision(input, options = {}) {
  if (typeof options.query !== "function") throw new Error("funder follow-up decision store invalid");
  const fields = decisionFields(input);
  const values = [input.tenant_id, fields.decisionId, input.outreach_id, input.candidate_id,
    input.status, fields.number, fields.dueAt, input.provider_thread_id, fields.inbound, input.observed_at];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_followup_decisions (
        tenant_id, decision_id, outreach_id, candidate_id, status, followup_number,
        due_at, provider_thread_id, inbound_message_id, observed_at
      ) VALUES ($1,$2,$3,$4,$5,$6,$7::timestamptz,$8,$9,$10::timestamptz)
      ON CONFLICT DO NOTHING RETURNING decision_id, true AS inserted
    ), replay AS (
      SELECT decision_id, false AS inserted FROM public.lm_funder_followup_decisions
      WHERE tenant_id=$1 AND decision_id=$2 AND outreach_id=$3 AND candidate_id=$4
        AND status=$5 AND followup_number IS NOT DISTINCT FROM $6
        AND due_at IS NOT DISTINCT FROM $7::timestamptz AND provider_thread_id=$8
        AND inbound_message_id IS NOT DISTINCT FROM $9 AND observed_at=$10::timestamptz
    )
    SELECT * FROM inserted UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, values);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("funder follow-up decision store conflict");
  return Object.freeze({ decision_id: fields.decisionId, ...result.rows[0] });
}

function validReceipt(receipt) {
  return receipt && receipt.schema_version === 1
    && /^funder-followup:[0-9a-f]{64}$/.test(String(receipt.followup_id || ""))
    && /^funder-outreach:[0-9a-f]{64}$/.test(String(receipt.outreach_id || ""))
    && /^funder-outreach-batch:[0-9a-f]{64}$/.test(String(receipt.batch_id || ""))
    && typeof receipt.tenant_id === "string" && receipt.tenant_id.length > 0
    && typeof receipt.candidate_id === "string" && receipt.candidate_id.length > 0
    && [1, 2].includes(receipt.followup_number)
    && Number.isFinite(Date.parse(receipt.due_at)) && Number.isFinite(Date.parse(receipt.sent_at))
    && Date.parse(receipt.sent_at) >= Date.parse(receipt.due_at)
    && /^[0-9a-f]{16,32}$/i.test(String(receipt.provider_message_id || ""))
    && /^[0-9a-f]{16,32}$/i.test(String(receipt.provider_thread_id || ""))
    && [receipt.rationale_sha256, receipt.subject_sha256, receipt.body_sha256].every((value) => DIGEST.test(String(value || "")));
}

async function appendFunderFollowupReceipt(receipt, options = {}) {
  if (!validReceipt(receipt) || typeof options.query !== "function") throw new Error("funder follow-up store invalid");
  const values = [receipt.tenant_id, receipt.followup_id, receipt.outreach_id, receipt.batch_id,
    receipt.candidate_id, receipt.followup_number, receipt.due_at, receipt.sent_at,
    receipt.provider_message_id, receipt.provider_thread_id, receipt.rationale_sha256,
    receipt.subject_sha256, receipt.body_sha256];
  const result = await options.query(`
    WITH inserted AS (
      INSERT INTO public.lm_funder_followup_ledger (
        tenant_id, followup_id, outreach_id, batch_id, candidate_id, followup_number,
        due_at, sent_at, provider_message_id, provider_thread_id,
        rationale_sha256, subject_sha256, body_sha256
      ) VALUES ($1,$2,$3,$4,$5,$6,$7::timestamptz,$8::timestamptz,$9,$10,$11,$12,$13)
      ON CONFLICT DO NOTHING RETURNING followup_id, true AS inserted
    ), replay AS (
      SELECT followup_id, false AS inserted FROM public.lm_funder_followup_ledger
      WHERE tenant_id=$1 AND followup_id=$2 AND outreach_id=$3 AND batch_id=$4
        AND candidate_id=$5 AND followup_number=$6 AND due_at=$7::timestamptz
        AND sent_at=$8::timestamptz AND provider_message_id=$9 AND provider_thread_id=$10
        AND rationale_sha256=$11 AND subject_sha256=$12 AND body_sha256=$13
    )
    SELECT * FROM inserted UNION ALL
    SELECT * FROM replay WHERE NOT EXISTS (SELECT 1 FROM inserted)
  `, values);
  if (!result || !Array.isArray(result.rows) || result.rows.length !== 1) throw new Error("funder follow-up store conflict");
  return Object.freeze({ ...result.rows[0] });
}

module.exports = { appendFunderFollowupDecision, appendFunderFollowupReceipt };
