"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildMarketplaceApplicationJob,
  marketplaceApplicationContract,
} = require("./marketplace-application-job.js");

function goalWorkItem() {
  return {
    job_id: "goal:goal-1",
    tenant_id: "tenant-1",
    loop_id: "life-manager.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: "intent-entry://tenant-1/goal-1" },
    max_attempts: 1,
  };
}

function input(overrides = {}) {
  return {
    goalWorkItem: goalWorkItem(),
    capabilityRef: "provider-capability://lancers/marketplace.application",
    opportunityRef: "marketplace-opportunity://lancers/job-123",
    intentRef: `application-intent://sha256/${"a".repeat(64)}`,
    authorizationRef: `authorization-receipt://sha256/${"b".repeat(64)}`,
    ...overrides,
  };
}

test("application identity is deterministic, reference-only, and authorization-bound", () => {
  const first = buildMarketplaceApplicationJob(input());
  const replay = buildMarketplaceApplicationJob(input());
  const changedAuthorization = buildMarketplaceApplicationJob(input({
    authorizationRef: `authorization-receipt://sha256/${"c".repeat(64)}`,
  }));
  assert.deepEqual(replay, first);
  assert.equal(first.effect_class, "publish");
  assert.equal(first.max_attempts, 1);
  assert.notEqual(changedAuthorization.effect_key, first.effect_key);
  assert.doesNotMatch(JSON.stringify(first), /proposal|account|credential|private/i);
  assert.deepEqual(marketplaceApplicationContract(first).input_refs, first.input_refs);
});

test("noncanonical parent or unbound references are rejected", () => {
  assert.throws(
    () => buildMarketplaceApplicationJob(input({
      goalWorkItem: { ...goalWorkItem(), effect_class: "publish" },
    })),
    /Goal WorkItem/i,
  );
  assert.throws(
    () => buildMarketplaceApplicationJob(input({ authorizationRef: "authorization-receipt://raw" })),
    /authorization reference/i,
  );
  assert.throws(
    () => buildMarketplaceApplicationJob(input({
      capabilityRef: "provider-capability://fiverr/marketplace.application",
    })),
    /provider mismatch/i,
  );
  const valid = buildMarketplaceApplicationJob(input());
  assert.throws(
    () => marketplaceApplicationContract({
      ...valid,
      input_refs: { ...valid.input_refs, extra_ref: "object://unexpected" },
    }),
    /job invalid/i,
  );
});
