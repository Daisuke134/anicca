"use strict";

const { enqueueJob: durableEnqueueJob } = require("./runtime-job-store.js");
const {
  buildMarketingVideoPublicationJob,
} = require("./marketing-video-publication-adapter.js");
const {
  verifyMarketingVideoGenerationReceipt,
} = require("./marketing-video-generation-adapter.js");

function buildVideoPublicationJobsFromGeneration(receipt, options = {}) {
  if (!verifyMarketingVideoGenerationReceipt(receipt)) {
    throw new Error("marketing video generation receipt is invalid");
  }
  const expectedProductId = String(options.productId || "").trim();
  if (!expectedProductId || expectedProductId !== receipt.product_id) {
    throw new Error("marketing video generation receipt product does not match expected product");
  }
  const shared = {
    tenantId: options.tenantId,
    productId: receipt.product_id,
    formatId: receipt.format_id,
    form: receipt.form,
    locale: receipt.locale,
    slot: receipt.slot,
    creativeId: receipt.creative_id,
    videoRef: receipt.video_ref,
    captionRef: options.captionRef || receipt.copy_ref,
    approvalRef: options.approvalRef,
    instagramProfileRef: options.instagramProfileRef,
    postizTokenRef: options.postizTokenRef,
    tiktokIntegrationRef: options.tiktokIntegrationRef,
  };
  return ["instagram", "tiktok"].map((platform) => (
    buildMarketingVideoPublicationJob({ ...shared, platform })
  ));
}

async function enqueueVideoGenerationPublications(receipt, options = {}, deps = {}) {
  const enqueueJob = deps.enqueueJob || durableEnqueueJob;
  const jobs = buildVideoPublicationJobsFromGeneration(receipt, options);
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
  buildVideoPublicationJobsFromGeneration,
  enqueueVideoGenerationPublications,
};
