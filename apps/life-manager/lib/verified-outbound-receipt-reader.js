"use strict";

const { isDeepStrictEqual } = require("node:util");

const { buildEventApplicationJob } = require("./outbound-event-job.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const { buildVerifiedOutboundReceipt } = require("./outbound-success.js");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");

const EVENT_REF = /^luma-event:\/\/event\/([A-Za-z0-9_-]+)\?starts_at=(.+)$/;
const RECEIPT_KEYS = Object.freeze([
  "artifact_ref",
  "attempt_ref",
  "canonical_url",
  "evidence_hash",
  "external_receipt_ref",
  "kind",
  "status",
  "verified_at",
]);

function invalid() { throw new Error("verified outbound receipt reader invalid"); }
function unavailable() { throw new Error("verified outbound receipt reader unavailable"); }

function nextDate(dateKey) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}

function exactStoredReceipt(value, expectedAttemptRef, expectedUrl) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== [...RECEIPT_KEYS].sort().join(",")
    || value.kind !== "outbound_event_application"
    || value.status !== "verified"
    || value.attempt_ref !== expectedAttemptRef
    || value.canonical_url !== expectedUrl
  ) unavailable();
  return value;
}

function exactJob(row, tenantId) {
  const refs = row && row.input_refs;
  const match = EVENT_REF.exec(String(refs && refs.event_ref || ""));
  if (
    !row || row.tenant_id !== tenantId || row.status !== "completed"
    || row.outcome !== "completed" || !match
    || !Number.isSafeInteger(Number(row.attempt)) || Number(row.attempt) < 1
  ) unavailable();
  let startsAt;
  try { startsAt = decodeURIComponent(match[2]); } catch { unavailable(); }
  let expected;
  try {
    expected = buildEventApplicationJob({
      tenantId,
      eventUrl: `https://luma.com/${match[1]}`,
      eventStartIso: startsAt,
      identityRef: refs.identity_ref,
      browserProfileRef: refs.browser_profile_ref,
      calendarRef: refs.calendar_ref,
    });
  } catch { unavailable(); }
  const comparable = Object.fromEntries([
    "job_id", "tenant_id", "loop_id", "capability", "effect_class",
    "effect_key", "input_refs", "max_attempts",
  ].map((key) => [key, row[key]]));
  if (!isDeepStrictEqual(comparable, expected)) unavailable();
  return Object.freeze({ ...expected, attempt: Number(row.attempt) });
}

function createVerifiedOutboundReceiptReader(dependencies = {}) {
  const query = dependencies.query;
  if (
    typeof query !== "function"
    || typeof dependencies.readExternalReceipt !== "function"
    || typeof dependencies.readArtifact !== "function"
    || typeof dependencies.fetchImpl !== "function"
  ) invalid();
  return Object.freeze({
    async listForCoverage(input = {}) {
      const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
      const coverage = input.coverage;
      if (
        !isVerifiedRollingEventCoverage(coverage)
        || !tenantId || coverage.tenant_id !== tenantId
      ) invalid();
      let rows;
      try {
        rows = (await query(`
          SELECT
            j.job_id, j.tenant_id, j.loop_id, j.capability, j.effect_class,
            j.effect_key, j.input_refs, j.max_attempts, j.attempt, j.status,
            r.outcome, r.receipt
          FROM public.lm_runtime_jobs j
          JOIN public.lm_runtime_job_receipts r
            ON r.job_id = j.job_id
            AND r.tenant_id = j.tenant_id
            AND r.attempt = j.attempt
          WHERE j.tenant_id = $1
            AND j.capability = 'outbound.event.apply'
            AND j.status = 'completed'
            AND r.outcome = 'completed'
            AND substring(j.input_refs->>'event_ref' from 'starts_at=([0-9]{4}-[0-9]{2}-[0-9]{2})') >= $2
            AND substring(j.input_refs->>'event_ref' from 'starts_at=([0-9]{4}-[0-9]{2}-[0-9]{2})') < $3
          ORDER BY j.job_id ASC
          LIMIT 500
        `, [tenantId, coverage.window_start_date, nextDate(coverage.window_end_date)])).rows;
      } catch { unavailable(); }
      if (!Array.isArray(rows) || rows.length > 500) unavailable();
      const results = [];
      try {
        for (const row of rows) {
          const job = exactJob(row, tenantId);
          const match = EVENT_REF.exec(job.input_refs.event_ref);
          const canonicalUrl = `https://luma.com/${match[1]}`;
          const expectedAttemptRef = `runtime-attempt://${tenantId}/${job.job_id}/${job.attempt}`;
          const stored = exactStoredReceipt(row.receipt, expectedAttemptRef, canonicalUrl);
          const evidence = await verifyOutboundEvidence({
            tenantId,
            attemptRef: expectedAttemptRef,
            externalReceiptRef: stored.external_receipt_ref,
            artifactRef: stored.artifact_ref,
            canonicalUrl: stored.canonical_url,
          }, dependencies);
          const receipt = buildVerifiedOutboundReceipt({
            tenantId,
            jobId: job.job_id,
            attempt: job.attempt,
            verifiedAt: stored.verified_at,
          }, evidence);
          results.push(Object.freeze({
            event_ref: job.input_refs.event_ref,
            job,
            receipt,
          }));
        }
      } catch { unavailable(); }
      return Object.freeze(results);
    },
  });
}

module.exports = { createVerifiedOutboundReceiptReader };
