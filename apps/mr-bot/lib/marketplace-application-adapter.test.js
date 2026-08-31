"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createMarketplaceApplicationLoopAdapter,
} = require("./marketplace-application-adapter.js");
const {
  buildMarketplaceApplicationJob,
} = require("./marketplace-application-job.js");

function goalWorkItem() {
  return {
    job_id: "goal-work-item:fixture",
    tenant_id: "tenant-a",
    loop_id: "mr-bot.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: "intent-entry://tenant-a/goal-1" },
    max_attempts: 1,
  };
}

function applicationJob() {
  return buildMarketplaceApplicationJob({
    goalWorkItem: goalWorkItem(),
    capabilityRef: "provider-capability://lancers/marketplace.application",
    opportunityRef: "marketplace-opportunity://lancers/project-1",
    intentRef: `application-intent://sha256/${"1".repeat(64)}`,
    authorizationRef: `authorization-receipt://sha256/${"2".repeat(64)}`,
  });
}

function receipt() {
  return Object.freeze({
    schema_version: 1,
    record_type: "application_receipt",
    platform: "lancers",
    opportunity_external_id: "project-1",
    application_external_id: "proposal-1",
    status: "verified",
    content_sha256: "1".repeat(64),
    idempotency_key: "lancers:application_receipt:proposal-1:v1",
    observed_at: "2026-08-28T13:00:00Z",
  });
}

test("adapter composes one bounded effect with official readback and replay zero", async () => {
  const job = applicationJob();
  const officialReceipt = receipt();
  let present = false;
  let executions = 0;
  const adapter = createMarketplaceApplicationLoopAdapter({
    async inspectApplication() {
      return present ? { state: "present", receipt: officialReceipt } : { state: "absent" };
    },
    async executeBoundedApplication(contract) {
      executions += 1;
      assert.equal(contract.job_id, job.job_id);
      assert.equal(Object.hasOwn(contract, "proposal"), false);
      present = true;
    },
    verifyReceipt(value) {
      assert.equal(value, officialReceipt);
      return value;
    },
  });

  const first = await adapter.execute(job);
  assert.equal(first.receipt, officialReceipt);
  assert.equal(first.effect_started, true);
  assert.equal(executions, 1);

  const replay = await adapter.execute(job);
  assert.equal(replay.receipt, officialReceipt);
  assert.equal(replay.replayed, true);
  assert.equal(executions, 1);
  assert.equal(adapter.verify(officialReceipt, job), true);
  assert.deepEqual(adapter.report(officialReceipt), {
    status: "verified",
    platform: "lancers",
    application_external_id: "proposal-1",
    observed_at: "2026-08-28T13:00:00Z",
  });
});

test("adapter keeps reconciliation unknown without an official provider proof", async () => {
  const adapter = createMarketplaceApplicationLoopAdapter();
  assert.deepEqual(await adapter.reconcile({ effectKey: "marketplace-application:v1:fixture" }), {
    state: "unknown",
  });
  assert.equal(adapter.verify(receipt(), applicationJob()), false);
});
