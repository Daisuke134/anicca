"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  STAGING_VERIFICATION_PLAN,
  createStagingVerificationReport,
} = require("../lib/mobile-staging-verification.js");

test("staging verification is an explicit, non-production plan until review", () => {
  assert.equal(STAGING_VERIFICATION_PLAN.environment, "staging_only");
  assert.equal(STAGING_VERIFICATION_PLAN.requiresCodeReview, true);
  assert.equal(STAGING_VERIFICATION_PLAN.productionMutation, false);
  assert.equal(STAGING_VERIFICATION_PLAN.migrationApplied, false);
  assert.equal(STAGING_VERIFICATION_PLAN.providerCallsExecuted, false);
  assert.ok(STAGING_VERIFICATION_PLAN.steps.length >= 8);
  assert.ok(STAGING_VERIFICATION_PLAN.evidenceRequired.length >= 5);
  assert.ok(STAGING_VERIFICATION_PLAN.stopConditions.length >= 4);
});

test("report cannot contain evidence before the code-review gate", () => {
  const planned = createStagingVerificationReport();
  assert.equal(planned.status, "planned_not_executed");
  assert.deepEqual(planned.evidence, []);
  assert.equal(planned.liveEvidence, false);
  assert.throws(
    () => createStagingVerificationReport({ evidence: [{ name: "bootstrap" }] }),
    /code_review_required/,
  );
});

test("reviewed report records supplied evidence without implying production", () => {
  const report = createStagingVerificationReport({
    codeReviewComplete: true,
    evidence: [{ name: "bootstrap", source: "staging-http-log" }],
  });
  assert.equal(report.status, "evidence_recorded_after_review");
  assert.equal(report.environment, "staging_only");
  assert.equal(report.productionMutation, false);
  assert.equal(report.liveEvidence, true);
  assert.deepEqual(report.evidence, [{ name: "bootstrap", source: "staging-http-log" }]);
});
