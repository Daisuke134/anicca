"use strict";

const { createHash } = require("node:crypto");

const { canonicalEventUrl } = require("./canonical-event-url.js");

const ATTEMPT_REF = /^runtime-attempt:\/\/([a-z0-9._-]+)\/[a-z0-9._:%-]+\/[1-9][0-9]*$/i;
const EXTERNAL_REF = /^(?:provider-receipt|gmail-message|ticket):\/\/[a-z0-9._-]+\/[a-z0-9._:~-]+$/i;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const RECEIPT_KINDS = new Set(["provider_response", "confirmation_mail", "ticket"]);
const PRODUCED_EVIDENCE = new WeakSet();

function text(value) {
  return String(value == null ? "" : value).trim();
}

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) deepFreeze(child);
  return Object.freeze(value);
}

function safeReceipt(value, ref) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const kind = text(value.kind);
  const expectedKind = ref.startsWith("gmail-message://")
    ? "confirmation_mail"
    : ref.startsWith("provider-receipt://")
      ? "provider_response"
      : "ticket";
  const providerId = text(value.provider_id);
  const observedAt = text(value.observed_at);
  if (
    !RECEIPT_KINDS.has(kind)
    || kind !== expectedKind
    || !providerId
    || providerId.length > 500
    || !Number.isFinite(Date.parse(observedAt))
    || !/[zZ]|[+-]\d\d:\d\d$/.test(observedAt)
  ) {
    return null;
  }
  return {
    kind,
    ref,
    provider_id: providerId,
    observed_at: new Date(Date.parse(observedAt)).toISOString(),
  };
}

async function verifyOutboundEvidence(input = {}, dependencies = {}) {
  const tenantId = text(input.tenantId);
  const attemptRef = text(input.attemptRef);
  const attemptMatch = ATTEMPT_REF.exec(attemptRef);
  const validAttempt = Boolean(tenantId && attemptMatch && attemptMatch[1] === tenantId);
  const externalReceiptRef = text(input.externalReceiptRef);
  const artifactRef = text(input.artifactRef);
  const artifactMatch = OBJECT_REF.exec(artifactRef);
  const url = canonicalEventUrl(input.canonicalUrl);
  const evidence = { e1: null, e2: null, e3: null };

  if (
    validAttempt
    && EXTERNAL_REF.test(externalReceiptRef)
    && typeof dependencies.readExternalReceipt === "function"
  ) {
    try {
      evidence.e1 = safeReceipt(
        await dependencies.readExternalReceipt(tenantId, externalReceiptRef),
        externalReceiptRef,
      );
    } catch {
      evidence.e1 = null;
    }
  }

  if (
    validAttempt
    && artifactMatch
    && typeof dependencies.readArtifact === "function"
  ) {
    try {
      const bytes = await dependencies.readArtifact(tenantId, artifactRef);
      const digest = Buffer.isBuffer(bytes)
        ? createHash("sha256").update(bytes).digest("hex")
        : "";
      if (
        Buffer.isBuffer(bytes)
        && bytes.length >= 5000
        && bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
        && digest === artifactMatch[1]
      ) {
        evidence.e2 = {
          ref: artifactRef,
          sha256: digest,
          size_bytes: bytes.length,
          media_type: "image/png",
        };
      }
    } catch {
      evidence.e2 = null;
    }
  }

  if (
    validAttempt
    && url
    && typeof dependencies.fetchImpl === "function"
  ) {
    try {
      const response = await dependencies.fetchImpl(url, {
        method: "HEAD",
        redirect: "manual",
        signal: AbortSignal.timeout(30_000),
      });
      if (response && response.status === 200) {
        evidence.e3 = { url, status_code: 200 };
      }
    } catch {
      evidence.e3 = null;
    }
  }

  const missing = ["E1", "E2", "E3"].filter((tier) => (
    evidence[tier.toLowerCase()] == null
  ));
  const result = {
    status: missing.length === 0 ? "verified" : "failed",
    attempt_ref: validAttempt ? attemptRef : null,
    missing,
    evidence,
  };
  const evidenceHash = createHash("sha256")
    .update(JSON.stringify(result), "utf8")
    .digest("hex");
  const produced = deepFreeze({ ...result, evidence_hash: evidenceHash });
  PRODUCED_EVIDENCE.add(produced);
  return produced;
}

function isVerifierProducedEvidence(value) {
  return Boolean(value && typeof value === "object" && PRODUCED_EVIDENCE.has(value));
}

module.exports = {
  verifyOutboundEvidence,
  isVerifierProducedEvidence,
};
