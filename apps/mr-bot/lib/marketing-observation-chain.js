"use strict";

const { enqueueJob: durableEnqueueJob } = require("./runtime-job-store.js");
const {
  verifyMarketingDailyReceipt,
} = require("./marketing-daily-adapter.js");
const {
  buildMarketingObservationJob,
} = require("./marketing-observation-adapter.js");

const WINDOWS = Object.freeze([
  ["2h", 2 * 60 * 60 * 1000],
  ["24h", 24 * 60 * 60 * 1000],
  ["72h", 72 * 60 * 60 * 1000],
  ["7d", 7 * 24 * 60 * 60 * 1000],
]);
const PUBLICATION_JOB_ID = /^marketing-daily:[0-9a-f]{64}$/;

function buildDueObservationJobs(publication, options = {}) {
  const jobId = String(publication && publication.job_id || "");
  const receipt = publication && publication.receipt;
  if (
    !PUBLICATION_JOB_ID.test(jobId)
    || !verifyMarketingDailyReceipt(receipt)
  ) {
    throw new Error("marketing publication observation source is invalid");
  }
  if (
    typeof receipt.provider_post_id !== "string"
    || !receipt.provider_post_id
    || typeof receipt.provider_route !== "string"
    || !receipt.provider_route
  ) {
    return [];
  }
  const nowMs = Number(options.nowMs);
  const publishedMs = Date.parse(receipt.published_at);
  if (!Number.isFinite(nowMs) || !Number.isFinite(publishedMs)) {
    throw new Error("marketing observation scan time is invalid");
  }
  return WINDOWS
    .filter(([, durationMs]) => nowMs >= publishedMs + durationMs)
    .map(([window]) => buildMarketingObservationJob({
      tenantId: options.tenantId,
      productId: options.productId,
      publicationJobId: jobId,
      window,
    }));
}

async function enqueueDueObservations(publication, options = {}, deps = {}) {
  const enqueueJob = deps.enqueueJob || durableEnqueueJob;
  const jobs = buildDueObservationJobs(publication, options);
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
  buildDueObservationJobs,
  enqueueDueObservations,
};
