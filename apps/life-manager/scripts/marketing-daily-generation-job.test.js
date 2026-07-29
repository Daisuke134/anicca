"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  enqueueMarketingDailyGeneration,
} = require("./marketing-daily-generation-job.js");

test("generation enqueue CLI creates one durable reference-only job", async () => {
  const refs = ["a", "b", "c", "d", "e"].map(
    (letter) => `object://sha256/${letter.repeat(64)}`,
  );
  const captured = [];
  const writes = [];
  await enqueueMarketingDailyGeneration([
    "enqueue",
    "--tenant", "tenant-a",
    "--date", "2026-07-30",
    "--bank-ref", refs[0],
    "--call-audio-ref", refs[1],
    "--stock-ref", refs[2],
    "--telegram-proof-ref", refs[3],
    "--whisper-ass-ref", refs[4],
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
  assert.equal(captured[0].inputRefs.date_ref, "calendar://date/2026-07-30");
  assert.doesNotMatch(JSON.stringify(captured[0]), /\.openclaw|\/Users\/|password|token/i);
  assert.equal(JSON.parse(writes[0]).created, true);
});
