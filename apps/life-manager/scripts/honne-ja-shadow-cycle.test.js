"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseArgs,
  runHonneJaShadowCycle,
} = require("./honne-ja-shadow-cycle.js");

const PACK_REF = `object://sha256/${"1".repeat(64)}`;
const MEDIA_REF = `object://sha256/${"2".repeat(64)}`;
const VIDEO_HASH = "2".repeat(64);
const COPY_HASH = "b".repeat(64);

function env(overrides = {}) {
  return {
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_HONNE_JA_PACK_REF: PACK_REF,
    LM_HONNE_JA_MEDIA_REFS: MEDIA_REF,
    LM_HONNE_JA_PUBLICATION_APPROVAL_REF: `object://sha256/${"c".repeat(64)}`,
    LM_HONNE_JA_INSTAGRAM_PROFILE_REF: "profile://instagram/life-manager",
    LM_HONNE_JA_POSTIZ_TOKEN_REF: "secret://postiz/api-key",
    LM_HONNE_JA_TIKTOK_INTEGRATION_REF: "integration://postiz/tiktok/life-manager",
    ...overrides,
  };
}

function generationReceipt(slot) {
  return {
    schema_version: 1,
    kind: "marketing_video_artifact",
    status: "ready",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot,
    creative_id: `HJA-008-${VIDEO_HASH.slice(0, 12)}`,
    hook_id: "HJA-008",
    hook_sha256: "e".repeat(64),
    video_ref: `object://sha256/${VIDEO_HASH}`,
    video_sha256: VIDEO_HASH,
    copy_ref: `object://sha256/${COPY_HASH}`,
    copy_sha256: COPY_HASH,
    generated_at: "2026-07-30T03:30:01.000Z",
  };
}

function fakeJobStore() {
  const jobs = new Map();
  const receipts = new Map();
  return {
    jobs,
    receipts,
    storeOptions: {},
    query: async () => ({ rows: [] }),
    async enqueueJob(input) {
      if (jobs.has(input.jobId)) return { created: false, job: jobs.get(input.jobId) };
      const job = {
        job_id: input.jobId,
        tenant_id: input.tenantId,
        loop_id: input.loopId,
        capability: input.capability,
        effect_class: input.effectClass,
        effect_key: input.effectKey,
        input_refs: input.inputRefs,
        max_attempts: input.maxAttempts,
        attempt: 1,
        status: "queued",
      };
      jobs.set(input.jobId, job);
      return { created: true, job };
    },
    async claimJobs({ capabilities }) {
      return [...jobs.values()].filter((job) => (
        job.status === "queued" && capabilities.includes(job.capability)
      )).slice(0, 1).map((job) => ({ ...job, status: "running" }));
    },
    async completeJob(input) {
      const job = jobs.get(input.jobId);
      job.status = "completed";
      receipts.set(input.jobId, input.receipt);
      return job;
    },
    async failJob(input) {
      jobs.get(input.jobId).status = "failed";
      return jobs.get(input.jobId);
    },
  };
}

test("cycle arguments require the run command and a well-formed optional slot", () => {
  assert.throws(() => parseArgs([]), /usage/i);
  assert.throws(() => parseArgs(["run", "--slot"]), /invalid/i);
  assert.throws(() => parseArgs(["run", "--bogus", "x"]), /invalid/i);
  assert.deepEqual(parseArgs(["run"]), {});
  assert.deepEqual(
    parseArgs(["run", "--slot", "2026-07-30T03:30:00.000Z"]),
    { slot: "2026-07-30T03:30:00.000Z" },
  );
});

test("one shadow cycle: real generation execution, publications enqueued and held, zero provider calls", async () => {
  const slot = "2026-07-30T03:30:00.000Z";
  const jobStore = fakeJobStore();
  const holds = [];
  let providerCalls = 0;
  const executed = [];

  const result = await runHonneJaShadowCycle(["run", "--slot", slot], {
    env: env(),
    jobStore,
    createHandlers: () => ({
      "marketing.video.generate": async (job) => {
        executed.push(job.job_id);
        return { receipt: generationReceipt(slot) };
      },
      "marketing.video.publish": async () => {
        providerCalls += 1;
        throw new Error("publication must never execute in shadow");
      },
    }),
    readGenerationReceipt: async (tenantId, jobId) => jobStore.receipts.get(jobId) || null,
    appendHold: async (hold) => { holds.push(hold); return "/tmp/held.jsonl"; },
  });

  // Generation really executed through the worker path and completed durably.
  assert.equal(executed.length, 1);
  assert.equal(result.generation.created, true);
  assert.equal(result.generation.hook_id, "HJA-008");
  assert.equal(result.generation.video_sha256, VIDEO_HASH);
  assert.equal(jobStore.jobs.get(result.generation.job_id).status, "completed");

  // Publication jobs exist in the durable store but are HELD: zero provider calls.
  assert.equal(result.publications.length, 2);
  assert.deepEqual(result.publications.map((entry) => entry.platform).sort(), [
    "platform://instagram",
    "platform://tiktok",
  ]);
  assert.ok(result.publications.every((entry) => entry.status === "queued"));
  assert.equal(providerCalls, 0);
  assert.equal(holds.length, 1);
  assert.equal(result.hold.status, "shadow_held");
  assert.equal(result.hold.ledger_path, "/tmp/held.jsonl");
});

test("replaying the same slot converges without new jobs or provider calls", async () => {
  const slot = "2026-07-30T03:30:00.000Z";
  const jobStore = fakeJobStore();
  const holds = [];
  const deps = {
    env: env(),
    jobStore,
    createHandlers: () => ({
      "marketing.video.generate": async () => ({ receipt: generationReceipt(slot) }),
    }),
    readGenerationReceipt: async (tenantId, jobId) => jobStore.receipts.get(jobId) || null,
    appendHold: async (hold) => { holds.push(hold); return "/tmp/held.jsonl"; },
  };
  await runHonneJaShadowCycle(["run", "--slot", slot], deps);
  const replay = await runHonneJaShadowCycle(["run", "--slot", slot], deps);
  assert.equal(replay.generation.created, false);
  assert.equal(jobStore.jobs.size, 3);
  assert.ok(replay.publications.every((entry) => entry.created === false));
  assert.ok(replay.publications.every((entry) => entry.status === "queued"));
});

test("cycle fails loudly when generation never completed", async () => {
  const jobStore = fakeJobStore();
  await assert.rejects(
    runHonneJaShadowCycle(["run", "--slot", "2026-07-30T03:30:00.000Z"], {
      env: env(),
      jobStore,
      createHandlers: () => ({}),
      readGenerationReceipt: async () => null,
      appendHold: async () => "/tmp/held.jsonl",
    }),
    /did not complete/i,
  );
});

test("without --slot the cycle refuses to run before the first slot of the local day", async () => {
  await assert.rejects(
    runHonneJaShadowCycle(["run"], {
      env: env(),
      nowMs: Date.parse("2026-07-30T02:00:00Z"), // 11:00 JST
      jobStore: fakeJobStore(),
      createHandlers: () => ({}),
      readGenerationReceipt: async () => null,
      appendHold: async () => "/tmp/held.jsonl",
    }),
    /no honne JA slot is due/i,
  );
});
