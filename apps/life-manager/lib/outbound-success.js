"use strict";

const {
  isVerifierProducedEvidence,
} = require("./outbound-evidence.js");

const VERIFIED_RECEIPTS = new WeakSet();

function required(value, label) {
  const result = String(value == null ? "" : value).trim();
  if (!result) throw new Error(`${label} is required`);
  return result;
}

function positiveAttempt(value) {
  const attempt = Number(value);
  if (!Number.isSafeInteger(attempt) || attempt < 1) {
    throw new Error("outbound attempt is invalid");
  }
  return attempt;
}

function attemptRef(input = {}) {
  return `runtime-attempt://${required(input.tenantId, "outbound tenant")}/${required(input.jobId, "outbound job")}/${positiveAttempt(input.attempt)}`;
}

function buildVerifiedOutboundReceipt(input = {}, evidence) {
  if (!isVerifierProducedEvidence(evidence)) {
    throw new Error("outbound evidence has no verifier provenance");
  }
  if (!evidence || evidence.status !== "verified" || evidence.missing.length !== 0) {
    throw new Error("outbound success requires verified evidence");
  }
  const expectedAttemptRef = attemptRef(input);
  if (evidence.attempt_ref !== expectedAttemptRef) {
    throw new Error("outbound evidence attempt mismatch");
  }
  const verifiedAt = input.verifiedAt == null
    ? new Date().toISOString()
    : new Date(Date.parse(required(input.verifiedAt, "verified at"))).toISOString();
  if (!Number.isFinite(Date.parse(verifiedAt))) throw new Error("verified at is invalid");
  const receipt = Object.freeze({
    kind: "outbound_event_application",
    status: "verified",
    attempt_ref: expectedAttemptRef,
    external_receipt_ref: evidence.evidence.e1.ref,
    artifact_ref: evidence.evidence.e2.ref,
    canonical_url: evidence.evidence.e3.url,
    evidence_hash: evidence.evidence_hash,
    verified_at: verifiedAt,
  });
  VERIFIED_RECEIPTS.add(receipt);
  return receipt;
}

function assertVerifiedOutboundReceipt(receipt, job = {}) {
  if (!receipt || !VERIFIED_RECEIPTS.has(receipt)) {
    const error = new Error("verified receipt provenance missing");
    error.unknownEffect = true;
    throw error;
  }
  const expected = attemptRef({
    tenantId: job.tenant_id,
    jobId: job.job_id,
    attempt: job.attempt,
  });
  if (receipt.attempt_ref !== expected) {
    const error = new Error("outbound receipt attempt mismatch");
    error.unknownEffect = true;
    throw error;
  }
  return receipt;
}

module.exports = {
  buildVerifiedOutboundReceipt,
  assertVerifiedOutboundReceipt,
};
