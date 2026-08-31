"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  enqueueMarketingVideoGeneration,
} = require("./marketing-video-generation-job.js");

test("video generation enqueue CLI creates one durable reference-only job", async () => {
  const refs = ["a", "b", "c"].map(
    (letter) => `object://sha256/${letter.repeat(64)}`,
  );
  const captured = [];
  const writes = [];
  await enqueueMarketingVideoGeneration([
    "enqueue",
    "--tenant", "tenant-a",
    "--product", "honne-ai",
    "--format", "reelclaw",
    "--locale", "ja",
    "--slot", "2026-07-30T12:30:00.000Z",
    "--pack-ref", refs[0],
    "--media-ref", refs[1],
    "--media-ref", refs[2],
  ], {
    enqueueJob: async (input) => {
      captured.push(input);
      return {
        created: true,
        job: {
          job_id: input.jobId,
          tenant_id: input.tenantId,
          capability: input.capability,
        },
      };
    },
    stdout: { write: (value) => writes.push(value) },
  });

  assert.equal(captured.length, 1);
  assert.equal(captured[0].effectClass, "none");
  assert.equal(captured[0].effectKey, null);
  assert.deepEqual(captured[0].inputRefs.media_refs, refs.slice(1));
  assert.doesNotMatch(
    JSON.stringify(captured[0]),
    /\.openclaw|\/Users\/|password|token/i,
  );
  assert.deepEqual(JSON.parse(writes[0]), {
    created: true,
    job_id: captured[0].jobId,
    tenant_id: "tenant-a",
    capability: "marketing.video.generate",
  });
});

test("video generation enqueue CLI rejects unknown or ambiguous arguments", async () => {
  await assert.rejects(
    enqueueMarketingVideoGeneration(["enqueue", "--tenant", "tenant-a"]),
    /--product is required/,
  );
  await assert.rejects(
    enqueueMarketingVideoGeneration([
      "enqueue",
      "--tenant", "tenant-a",
      "--tenant", "tenant-b",
    ]),
    /unique/i,
  );
});
