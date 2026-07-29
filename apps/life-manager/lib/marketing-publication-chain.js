"use strict";

const { enqueueJob: durableEnqueueJob } = require("./runtime-job-store.js");
const {
  buildMarketingDailyJob,
} = require("./marketing-daily-adapter.js");
const {
  verifyMarketingDailyGenerationReceipt,
} = require("./marketing-daily-generation-adapter.js");

function buildPublicationJobsFromGeneration(receipt, options = {}) {
  if (!verifyMarketingDailyGenerationReceipt(receipt)) {
    throw new Error("marketing generation receipt is invalid");
  }
  const shared = {
    tenantId: options.tenantId,
    creativeId: receipt.creative_id,
    videoRef: receipt.video_ref,
    captionRef: options.captionRef,
    approvalRef: options.approvalRef,
    instagramProfileRef: "profile://instagram/life-manager",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/life-manager",
  };
  return ["instagram", "tiktok"].map((platform) => (
    buildMarketingDailyJob({ ...shared, platform })
  ));
}

async function enqueueGenerationPublications(receipt, options = {}, deps = {}) {
  const enqueueJob = deps.enqueueJob || durableEnqueueJob;
  const jobs = buildPublicationJobsFromGeneration(receipt, options);
  return Promise.all(jobs.map((job) => enqueueJob({
    jobId: job.job_id,
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    capability: job.capability,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    inputRefs: job.input_refs,
    maxAttempts: job.max_attempts,
  }, deps.storeOptions || {})));
}

module.exports = {
  buildPublicationJobsFromGeneration,
  enqueueGenerationPublications,
};
