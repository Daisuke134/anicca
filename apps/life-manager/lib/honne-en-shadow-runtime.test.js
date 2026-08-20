"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  HONNE_EN_SLOTS,
  holdHonneEnShadowPublications,
  honneEnShadowConfig,
  honneEnShadowStatus,
  planHonneEnShadowGeneration,
} = require("./honne-en-shadow-runtime.js");

const objectRef = (character) => `object://sha256/${character.repeat(64)}`;

function activeEnv(overrides = {}) {
  return {
    LM_HONNE_EN_SHADOW_ENABLED: "true",
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_HONNE_EN_PACK_REF: objectRef("1"),
    LM_HONNE_EN_MEDIA_REFS: `${objectRef("2")},${objectRef("3")}`,
    LM_HONNE_EN_PUBLICATION_APPROVAL_REF: objectRef("c"),
    LM_HONNE_EN_INSTAGRAM_PROFILE_REF: "profile://instagram/honne_reveal",
    LM_HONNE_EN_POSTIZ_TOKEN_REF: "secret://postiz/api-key",
    LM_HONNE_EN_TIKTOK_INTEGRATION_REF: "integration://postiz/tiktok/cmoig11ew001zlv0yk6vqo1us",
    ...overrides,
  };
}

function generationReceipt(slot = "2026-08-20T02:00:00.000Z") {
  return {
    schema_version: 1,
    kind: "marketing_video_artifact",
    status: "ready",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "en",
    slot,
    creative_id: "HEN-001-aaaaaaaaaaaa",
    hook_id: "HEN-001",
    hook_sha256: "e".repeat(64),
    video_ref: objectRef("a"),
    video_sha256: "a".repeat(64),
    copy_ref: objectRef("b"),
    copy_sha256: "b".repeat(64),
    generated_at: new Date(Date.parse(slot) + 1000).toISOString(),
  };
}

function fakeStore() {
  const jobs = new Map();
  return {
    jobs,
    async enqueueJobAt(input, availableAt) {
      if (jobs.has(input.jobId)) return { created: false, job: jobs.get(input.jobId) };
      const job = { job_id: input.jobId, capability: input.capability, input_refs: input.inputRefs, status: "queued", available_at: availableAt };
      jobs.set(input.jobId, job);
      return { created: true, job };
    },
    async claimJobs(capabilities, nowMs) {
      return [...jobs.values()].filter((job) => (
        job.status === "queued"
        && capabilities.includes(job.capability)
        && Date.parse(job.available_at) <= nowMs
      ));
    },
  };
}

test("Honne EN is default-off and encodes only 07:00/11:00/20:30 Asia/Tokyo", () => {
  const disabled = honneEnShadowConfig({});
  assert.equal(disabled.enabled, false);
  assert.deepEqual([...disabled.slots], HONNE_EN_SLOTS);
  assert.equal(planHonneEnShadowGeneration(disabled, Date.parse("2026-08-20T11:31:00Z")), null);

  const config = honneEnShadowConfig(activeEnv());
  const expected = [
    ["2026-08-19T22:01:00Z", "2026-08-19T22:00:00.000Z"],
    ["2026-08-20T02:01:00Z", "2026-08-20T02:00:00.000Z"],
    ["2026-08-20T11:31:00Z", "2026-08-20T11:30:00.000Z"],
  ];
  for (const [now, slot] of expected) {
    const job = planHonneEnShadowGeneration(config, Date.parse(now));
    assert.equal(job.input_refs.slot_ref, `schedule-slot://${slot}`);
    assert.equal(job.input_refs.product_ref, "product://honne-ai");
    assert.equal(job.input_refs.locale_ref, "locale://en");
  }
});

test("Honne EN shadow holds provider writes, preserves lineage, and replay creates no jobs", async () => {
  const config = honneEnShadowConfig(activeEnv());
  const store = fakeStore();
  const holds = [];
  let providerWrites = 0;
  const deps = {
    enqueueJobAt: store.enqueueJobAt,
    appendHold: async (hold) => holds.push(hold),
    runDistribution: () => { providerWrites += 1; },
  };
  await holdHonneEnShadowPublications(generationReceipt(), config, deps);
  const replay = await holdHonneEnShadowPublications(generationReceipt(), config, deps);

  assert.equal(providerWrites, 0);
  assert.equal(store.jobs.size, 2);
  assert.equal(holds.length, 1);
  assert.equal(replay.recorded, false);
  const tiktok = [...store.jobs.values()].find((job) => job.input_refs.platform_ref === "platform://tiktok");
  assert.equal(tiktok.status, "queued");
  assert.equal(tiktok.available_at, "9999-12-31T23:59:59.000Z");
  assert.ok(Date.parse(tiktok.available_at) > Date.now());
  assert.deepEqual(
    await store.claimJobs(["marketing.video.publish"], Date.parse("2026-08-20T12:00:00Z")),
    [],
  );
  assert.equal(tiktok.input_refs.product_ref, "product://honne-ai");
  assert.equal(tiktok.input_refs.locale_ref, "locale://en");
  assert.equal(tiktok.input_refs.tiktok_integration_ref, "integration://postiz/tiktok/cmoig11ew001zlv0yk6vqo1us");
  assert.match(tiktok.input_refs.creative_ref, /^creative:\/\/honne-ai\/HEN-001-/);
});

test("Honne EN status exposes a stopped scheduler as a missed expected slot", () => {
  const first = generationReceipt("2026-08-19T22:00:00.000Z");
  const status = honneEnShadowStatus([{
    outcome: "completed",
    receipt: first,
    created_at: first.generated_at,
  }], { nowMs: Date.parse("2026-08-20T02:05:00.000Z") });
  assert.equal(status.consecutive, 0);
  assert.deepEqual(status.missed_slots, ["2026-08-20T02:00:00.000Z"]);
});
