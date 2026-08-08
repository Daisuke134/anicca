"use strict";

function freeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) freeze(child);
  return Object.freeze(value);
}

const STAGING_VERIFICATION_PLAN = freeze({
  version: "gate3-mobile-staging-v1",
  environment: "staging_only",
  requiresCodeReview: true,
  productionMutation: false,
  migrationApplied: false,
  providerCallsExecuted: false,
  steps: [
    "Apply the mobile Gate 3 migration only to an isolated staging database after code review.",
    "Exchange a staging identity and verify access/refresh rotation plus rotated-token family replay.",
    "Read bootstrap/profile and verify the frozen contract fixtures, including the IANA calendar timezone.",
    "Run analysis against staging structured transit/Google providers and verify route_ready, cache reuse, and route_unavailable boundaries.",
    "Read chat with a cursor, reply to a question, force a downstream retry, and verify claim/apply/outbox resumption.",
    "Register and transfer an APNs token only within the staging APNs environment matrix.",
    "Place a confirmed test call only with an explicitly approved staging number and verify user/global day guards.",
    "Delete a disposable staging account and verify provider cleanup precedes terminal revocation plus capability replay.",
  ],
  evidenceRequired: [
    "HTTP status/body capture with request IDs for each contract endpoint.",
    "Staging database rows showing session family, idempotency expiry, outbox cursor, day guard, and deletion receipt transitions.",
    "Structured route provider/cache logs with IANA timezone preserved end-to-end.",
    "APNs ownership transfer and call-cap race results from isolated staging identities.",
    "Provider cleanup and post-revocation capability replay record for a disposable staging account.",
  ],
  stopConditions: [
    "Any endpoint resolves to production configuration or a production database.",
    "Any provider credential or real user/device/phone is required outside the approved staging fixture.",
    "A migration, deletion, call, or APNs registration would affect a non-disposable tenant.",
    "An unknown or invalid timezone is silently converted to UTC.",
  ],
});

function createStagingVerificationReport(options = {}) {
  const codeReviewComplete = options.codeReviewComplete === true;
  const evidence = Array.isArray(options.evidence) ? options.evidence.map((item) => ({ ...item })) : [];
  if (evidence.length > 0 && !codeReviewComplete) {
    throw new Error("code_review_required");
  }
  const status = evidence.length > 0
    ? "evidence_recorded_after_review"
    : codeReviewComplete ? "reviewed_not_executed" : "planned_not_executed";
  return freeze({
    ...STAGING_VERIFICATION_PLAN,
    status,
    codeReviewComplete,
    liveEvidence: evidence.length > 0,
    evidence,
  });
}

module.exports = { STAGING_VERIFICATION_PLAN, createStagingVerificationReport };
