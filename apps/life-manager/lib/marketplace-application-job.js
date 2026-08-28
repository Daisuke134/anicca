"use strict";

const { createHash } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");
const { buildRuntimeJob } = require("./runtime-job-store.js");

const LOOP_ID = "life-manager.manager";
const CAPABILITY = "marketplace.application";
const HASH = /^[0-9a-f]{64}$/;

function reference(value, prefix, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text.startsWith(prefix)) throw new Error(`${label} reference invalid`);
  return text;
}

function hashReference(value, prefix, label) {
  const text = reference(value, prefix, label);
  if (!HASH.test(text.slice(prefix.length))) throw new Error(`${label} reference invalid`);
  return text;
}

function providerReference(value, prefix, label) {
  const text = reference(value, prefix, label);
  const parts = text.slice(prefix.length).split("/");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`${label} reference invalid`);
  }
  return { text, provider: parts[0], resource: parts[1] };
}

function parentGoal(job) {
  const keys = job && job.input_refs && Object.keys(job.input_refs);
  if (
    !job
    || job.loop_id !== LOOP_ID
    || job.capability !== "general-agent.work"
    || job.effect_class !== "none"
    || job.effect_key !== null
    || job.max_attempts !== 1
    || JSON.stringify(keys) !== JSON.stringify(["goal_ref"])
  ) throw new Error("canonical Goal WorkItem required");
  const goalPrefix = `intent-entry://${encodeURIComponent(job.tenant_id)}/`;
  if (!String(job.input_refs.goal_ref || "").startsWith(goalPrefix)) {
    throw new Error("canonical Goal WorkItem required");
  }
  return job;
}

function buildMarketplaceApplicationJob(input = {}) {
  const parent = parentGoal(input.goalWorkItem);
  const capability = providerReference(
    input.capabilityRef,
    "provider-capability://",
    "capability",
  );
  const opportunity = providerReference(
    input.opportunityRef,
    "marketplace-opportunity://",
    "opportunity",
  );
  if (capability.resource !== "marketplace.application") {
    throw new Error("capability reference invalid");
  }
  if (capability.provider !== opportunity.provider) {
    throw new Error("provider mismatch");
  }
  const refs = {
    goal_ref: reference(parent.input_refs.goal_ref, "intent-entry://", "goal"),
    capability_ref: capability.text,
    opportunity_ref: opportunity.text,
    intent_ref: hashReference(input.intentRef, "application-intent://sha256/", "intent"),
    authorization_ref: hashReference(
      input.authorizationRef,
      "authorization-receipt://sha256/",
      "authorization",
    ),
  };
  const digest = createHash("sha256")
    .update(JSON.stringify([parent.tenant_id, ...Object.values(refs)]), "utf8")
    .digest("hex");
  return buildRuntimeJob({
    jobId: `marketplace-application:${digest}`,
    tenantId: parent.tenant_id,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "publish",
    effectKey: `marketplace-application:v1:${digest}`,
    inputRefs: refs,
    maxAttempts: 1,
  });
}

function marketplaceApplicationContract(job) {
  const refs = job && job.input_refs;
  const expected = buildMarketplaceApplicationJob({
    goalWorkItem: {
      tenant_id: job && job.tenant_id,
      loop_id: LOOP_ID,
      capability: "general-agent.work",
      effect_class: "none",
      effect_key: null,
      input_refs: { goal_ref: refs && refs.goal_ref },
      max_attempts: 1,
    },
    capabilityRef: refs && refs.capability_ref,
    opportunityRef: refs && refs.opportunity_ref,
    intentRef: refs && refs.intent_ref,
    authorizationRef: refs && refs.authorization_ref,
  });
  for (const key of [
    "job_id",
    "tenant_id",
    "loop_id",
    "capability",
    "effect_class",
    "effect_key",
    "max_attempts",
  ]) {
    if (!job || job[key] !== expected[key]) {
      throw new Error("marketplace application job invalid");
    }
  }
  if (!isDeepStrictEqual(job.input_refs, expected.input_refs)) {
    throw new Error("marketplace application job invalid");
  }
  return Object.freeze({
    tenant_id: job.tenant_id,
    job_id: job.job_id,
    effect_key: job.effect_key,
    input_refs: Object.freeze({ ...refs }),
  });
}

module.exports = {
  LOOP_ID,
  CAPABILITY,
  buildMarketplaceApplicationJob,
  marketplaceApplicationContract,
};
