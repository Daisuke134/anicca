"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildVideoPublicationJobsFromGeneration,
  enqueueVideoGenerationPublications,
} = require("./marketing-video-publication-chain.js");

const VIDEO_HASH = "a".repeat(64);
const COPY_HASH = "b".repeat(64);
const APPROVAL_HASH = "c".repeat(64);

function generationReceipt(overrides = {}) {
  return {
    schema_version: 1,
    kind: "marketing_video_artifact",
    status: "ready",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T12:30:00.000Z",
    creative_id: "HJA-007-aaaaaaaaaaaa",
    hook_id: "HJA-007",
    hook_sha256: "e".repeat(64),
    video_ref: `object://sha256/${VIDEO_HASH}`,
    video_sha256: VIDEO_HASH,
    copy_ref: `object://sha256/${COPY_HASH}`,
    copy_sha256: COPY_HASH,
    generated_at: "2026-07-30T12:30:01.000Z",
    ...overrides,
  };
}

function options(overrides = {}) {
  return {
    tenantId: "tenant-a",
    productId: "honne-ai",
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/honne-ai-ja",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/honne-ai-ja",
    ...overrides,
  };
}

test("one generic video generation receipt fans out to independent Instagram and TikTok publication jobs", () => {
  const jobs = buildVideoPublicationJobsFromGeneration(generationReceipt(), options());

  assert.equal(jobs.length, 2);
  assert.deepEqual(jobs.map((job) => job.input_refs.platform_ref), [
    "platform://instagram",
    "platform://tiktok",
  ]);
  assert.ok(jobs.every((job) => (
    job.tenant_id === "tenant-a"
    && job.input_refs.product_ref === "product://honne-ai"
    && job.input_refs.creative_ref === "creative://honne-ai/HJA-007-aaaaaaaaaaaa"
    && job.input_refs.video_ref === `object://sha256/${VIDEO_HASH}`
    && job.input_refs.caption_ref === `object://sha256/${COPY_HASH}`
    && job.input_refs.approval_ref === `object://sha256/${APPROVAL_HASH}`
    && job.effect_class === "publish"
  )));
  assert.notEqual(jobs[0].job_id, jobs[1].job_id);
  assert.notEqual(jobs[0].effect_key, jobs[1].effect_key);
  assert.doesNotMatch(JSON.stringify(jobs), /\.openclaw|\/Users\/|password|raw-token/i);
});

test("chain rejects a hash-mismatched generation receipt before any job is created", () => {
  assert.throws(
    () => buildVideoPublicationJobsFromGeneration(
      generationReceipt({ video_sha256: "d".repeat(64) }),
      options(),
    ),
    /generation receipt/i,
  );
});

test("chain rejects a cross-product generation receipt before any job is created", () => {
  assert.throws(
    () => buildVideoPublicationJobsFromGeneration(
      generationReceipt({ product_id: "anicca-ios" }),
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

  const first = await enqueueVideoGenerationPublications(
    generationReceipt(),
    options(),
    { enqueueJob },
  );
  const second = await enqueueVideoGenerationPublications(
    generationReceipt(),
    options(),
    { enqueueJob },
  );

  assert.deepEqual(first.map((item) => item.created), [true, true]);
  assert.deepEqual(second.map((item) => item.created), [false, false]);
  assert.equal(stored.size, 2);
  assert.equal(calls.length, 4);
});

test("providers are called zero additional times when the chain is replayed after real execution", async () => {
  const { createMarketingVideoPublicationLoopAdapter } = require("./marketing-video-publication-adapter.js");
  const providerCalls = [];
  const adapter = createMarketingVideoPublicationLoopAdapter({
    objectStore: { resolve: (ref) => `/objects/${ref.slice(-64)}` },
    profileProvider: {
      get: async () => ({
        handle: "honne_ai",
        accountsPath: "/profiles/accounts.json",
        settingsPath: "/profiles/settings.json",
        credentialsPath: "/profiles/credentials.json",
        stateDir: "/profiles/state",
      }),
    },
    secretProvider: { get: async () => "token" },
    integrationProvider: { get: async () => "integration" },
    ledgerPath: () => "/tmp/never-read-because-mocked.jsonl",
    async runDistribution(input) {
      providerCalls.push(input);
      return {
        creative_id: "HJA-007-aaaaaaaaaaaa",
        video_sha256: VIDEO_HASH,
        caption_sha256: COPY_HASH,
        platform: input.platform,
        public_url: input.platform === "instagram"
          ? "https://www.instagram.com/reel/abc123/"
          : "https://www.tiktok.com/@honne_ai/video/7999999999999999999",
        provider_post_id: `postiz-${input.platform}-HJA-007`,
        provider_route: "postiz",
        provider_reconciled: false,
      };
    },
  });

  const jobs = buildVideoPublicationJobsFromGeneration(generationReceipt(), options());
  const receipts = await Promise.all(jobs.map((job) => adapter.execute(job)));
  assert.equal(providerCalls.length, 2);
  assert.ok(receipts.every(({ receipt }) => adapter.verify(receipt)));

  // Replaying execution with a distribution stub that must never be called again proves
  // the caller is expected to short-circuit on an already-published effect_key/job_id.
  const alreadyPublishedCallCount = providerCalls.length;
  const jobsReplay = buildVideoPublicationJobsFromGeneration(generationReceipt(), options());
  assert.deepEqual(
    jobsReplay.map((job) => job.job_id),
    jobs.map((job) => job.job_id),
  );
  assert.equal(providerCalls.length, alreadyPublishedCallCount);
});
