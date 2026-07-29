"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildDueObservationJobs,
  enqueueDueObservations,
} = require("./marketing-observation-chain.js");

const VIDEO_HASH = "a".repeat(64);
const CAPTION_HASH = "b".repeat(64);
const PUBLICATION_JOB_ID = `marketing-daily:${"c".repeat(64)}`;

function publication() {
  return {
    job_id: PUBLICATION_JOB_ID,
    receipt: {
      schema_version: 1,
      kind: "marketing_daily_distribution",
      status: "published",
      creative_id: "B01",
      platform: "tiktok",
      video_sha256: VIDEO_HASH,
      caption_sha256: CAPTION_HASH,
      public_url: "https://www.tiktok.com/@life_manager/video/7999999999999999999",
      provider_post_id: "postiz-post-B01",
      provider_route: "postiz",
      provider_reconciled: false,
      published_at: "2026-07-29T12:00:00.000Z",
    },
  };
}

test("one publication independently creates only observation windows that are due", () => {
  const jobs = buildDueObservationJobs(publication(), {
    tenantId: "tenant-a",
    productId: "life-manager",
    nowMs: Date.parse("2026-07-30T13:00:00.000Z"),
  });

  assert.deepEqual(
    jobs.map((job) => job.input_refs.observation_window_ref),
    ["metric-window://2h", "metric-window://24h"],
  );
  assert.ok(jobs.every((job) => (
    job.tenant_id === "tenant-a"
    && job.input_refs.product_ref === "product://life-manager"
    && job.input_refs.publication_receipt_ref
      === `runtime-receipt://${PUBLICATION_JOB_ID}`
  )));
  assert.equal(new Set(jobs.map((job) => job.job_id)).size, 2);
});

test("a publication with no due window creates no observation job", () => {
  const jobs = buildDueObservationJobs(publication(), {
    tenantId: "tenant-a",
    productId: "life-manager",
    nowMs: Date.parse("2026-07-29T13:59:59.999Z"),
  });
  assert.deepEqual(jobs, []);
});

test("historical receipts without provider metric join keys are skipped safely", () => {
  const historical = publication();
  delete historical.receipt.provider_post_id;
  delete historical.receipt.provider_route;
  assert.deepEqual(buildDueObservationJobs(historical, {
    tenantId: "tenant-a",
    productId: "life-manager",
    nowMs: Date.parse("2026-08-10T00:00:00.000Z"),
  }), []);
});

test("repeated scans enqueue deterministic jobs and rely on durable idempotency", async () => {
  const stored = new Set();
  const enqueueJob = async (input) => {
    const created = !stored.has(input.jobId);
    stored.add(input.jobId);
    return { created, job: { job_id: input.jobId } };
  };
  const options = {
    tenantId: "tenant-a",
    productId: "life-manager",
    nowMs: Date.parse("2026-08-10T00:00:00.000Z"),
  };

  const first = await enqueueDueObservations(publication(), options, {
    enqueueJob,
  });
  const second = await enqueueDueObservations(publication(), options, {
    enqueueJob,
  });

  assert.deepEqual(first.map((value) => value.created), [true, true, true, true]);
  assert.deepEqual(second.map((value) => value.created), [false, false, false, false]);
  assert.equal(stored.size, 4);
});
