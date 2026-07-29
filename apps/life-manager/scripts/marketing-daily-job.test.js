"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { enqueueMarketingDaily } = require("./marketing-daily-job.js");

test("enqueue CLI builds one durable reference-only marketing job", async () => {
  const output = [];
  const calls = [];
  const args = [
    "enqueue",
    "--tenant", "tenant-a",
    "--creative", "B01",
    "--platform", "tiktok",
    "--video-ref", `object://sha256/${"a".repeat(64)}`,
    "--caption-ref", `object://sha256/${"b".repeat(64)}`,
    "--approval-ref", `object://sha256/${"c".repeat(64)}`,
  ];
  await enqueueMarketingDaily(args, {}, {
    enqueueJob: async (job) => {
      calls.push(job);
      return { created: true, job: {
        job_id: job.jobId,
        tenant_id: job.tenantId,
        capability: job.capability,
        effect_key: job.effectKey,
      } };
    },
    stdout: { write: (value) => output.push(value) },
  });

  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].inputRefs, {
    creative_ref: "creative://life-manager/B01",
    platform_ref: "platform://tiktok",
    video_ref: `object://sha256/${"a".repeat(64)}`,
    caption_ref: `object://sha256/${"b".repeat(64)}`,
    approval_ref: `object://sha256/${"c".repeat(64)}`,
    instagram_profile_ref: "profile://instagram/life-manager",
    postiz_token_ref: "secret://postiz/api-key",
    tiktok_integration_ref: "integration://postiz/tiktok/life-manager",
  });
  assert.equal(JSON.parse(output[0]).created, true);
});
