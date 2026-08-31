"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildPublicationJobsFromGeneration,
  enqueueGenerationPublications,
} = require("./marketing-publication-chain.js");

const VIDEO_HASH = "a".repeat(64);
const CAPTION_HASH = "b".repeat(64);
const APPROVAL_HASH = "c".repeat(64);

function generationReceipt(overrides = {}) {
  return {
    schema_version: 1,
    kind: "marketing_daily_generation",
    status: "rendered",
    date: "2026-08-01",
    creative_id: "A03",
    video_ref: `object://sha256/${VIDEO_HASH}`,
    video_sha256: VIDEO_HASH,
    duration_seconds: 34.666667,
    generated_at: "2026-07-29T15:00:00.000Z",
    ...overrides,
  };
}

function options() {
  return {
    tenantId: "tenant-a",
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
  };
}

test("one generation receipt fans out to independent Instagram and TikTok publication jobs", () => {
  const jobs = buildPublicationJobsFromGeneration(generationReceipt(), options());

  assert.equal(jobs.length, 2);
  assert.deepEqual(jobs.map((job) => job.input_refs.platform_ref), [
    "platform://instagram",
    "platform://tiktok",
  ]);
  assert.ok(jobs.every((job) => (
    job.tenant_id === "tenant-a"
    && job.input_refs.video_ref === `object://sha256/${VIDEO_HASH}`
    && job.input_refs.caption_ref === `object://sha256/${CAPTION_HASH}`
    && job.input_refs.approval_ref === `object://sha256/${APPROVAL_HASH}`
    && job.effect_class === "publish"
  )));
  assert.notEqual(jobs[0].job_id, jobs[1].job_id);
  assert.notEqual(jobs[0].effect_key, jobs[1].effect_key);
  assert.doesNotMatch(JSON.stringify(jobs), /\.openclaw|\/Users\/|password|raw-token/i);
});

test("publication chain rejects an unverified generation receipt", () => {
  assert.throws(
    () => buildPublicationJobsFromGeneration(
      generationReceipt({ video_sha256: "d".repeat(64) }),
      options(),
    ),
    /generation receipt/i,
  );
});

test("repeated chain scans enqueue the same deterministic jobs and depend on store idempotency", async () => {
  const stored = new Map();
  const calls = [];
  const enqueueJob = async (input) => {
    calls.push(input);
    const created = !stored.has(input.jobId);
    if (created) stored.set(input.jobId, input);
    return {
      created,
      job: {
        job_id: input.jobId,
        tenant_id: input.tenantId,
        capability: input.capability,
      },
    };
  };

  const first = await enqueueGenerationPublications(
    generationReceipt(),
    options(),
    { enqueueJob },
  );
  const second = await enqueueGenerationPublications(
    generationReceipt(),
    options(),
    { enqueueJob },
  );

  assert.deepEqual(first.map((item) => item.created), [true, true]);
  assert.deepEqual(second.map((item) => item.created), [false, false]);
  assert.equal(stored.size, 2);
  assert.equal(calls.length, 4);
});
