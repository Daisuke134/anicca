"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  EXPECTED_SHADOW_CYCLES,
  SHADOW_HOLD_STATUS,
  appendHonneJaShadowHold,
  holdHonneJaShadowPublications,
  honneJaShadowConfig,
  honneJaShadowStatus,
  planHonneJaShadowGeneration,
} = require("./honne-ja-shadow-runtime.js");

const PACK_REF = `object://sha256/${"1".repeat(64)}`;
const MEDIA_REF_A = `object://sha256/${"2".repeat(64)}`;
const MEDIA_REF_B = `object://sha256/${"3".repeat(64)}`;
const VIDEO_HASH = "a".repeat(64);
const COPY_HASH = "b".repeat(64);
const APPROVAL_REF = `object://sha256/${"c".repeat(64)}`;

function activeEnv(overrides = {}) {
  return {
    LM_HONNE_JA_SHADOW_ENABLED: "true",
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_HONNE_JA_PACK_REF: PACK_REF,
    LM_HONNE_JA_MEDIA_REFS: `${MEDIA_REF_A},${MEDIA_REF_B}`,
    LM_HONNE_JA_PUBLICATION_APPROVAL_REF: APPROVAL_REF,
    LM_HONNE_JA_INSTAGRAM_PROFILE_REF: "profile://instagram/life-manager",
    LM_HONNE_JA_POSTIZ_TOKEN_REF: "secret://postiz/api-key",
    LM_HONNE_JA_TIKTOK_INTEGRATION_REF: "integration://postiz/tiktok/life-manager",
    ...overrides,
  };
}

function generationReceipt(overrides = {}) {
  return {
    schema_version: 1,
    kind: "marketing_video_artifact",
    status: "ready",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T03:30:00.000Z",
    creative_id: "HJA-008-aaaaaaaaaaaa",
    hook_id: "HJA-008",
    hook_sha256: "e".repeat(64),
    video_ref: `object://sha256/${VIDEO_HASH}`,
    video_sha256: VIDEO_HASH,
    copy_ref: `object://sha256/${COPY_HASH}`,
    copy_sha256: COPY_HASH,
    generated_at: "2026-07-30T03:30:01.000Z",
    ...overrides,
  };
}

function fakeDurableStore() {
  const jobs = new Map();
  return {
    jobs,
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
        status: "queued",
      };
      jobs.set(input.jobId, job);
      return { created: true, job };
    },
  };
}

// ── Default-off contract ─────────────────────────────────────────────────────

test("shadow scheduler config defaults OFF with no configuration at all", () => {
  const config = honneJaShadowConfig({});
  assert.equal(config.enabled, false);
  assert.ok(Object.isFrozen(config));
  assert.deepEqual([...config.slots], ["12:30", "21:30"]);
  assert.equal(config.timeZone, "Asia/Tokyo");
});

test("only the exact deliberate value true enables; every other value stays OFF", () => {
  for (const value of ["1", "yes", "on", "TRUE-ish", "", "false", "0"]) {
    assert.equal(
      honneJaShadowConfig(activeEnv({ LM_HONNE_JA_SHADOW_ENABLED: value })).enabled,
      false,
      `LM_HONNE_JA_SHADOW_ENABLED=${JSON.stringify(value)} must stay off`,
    );
  }
  assert.equal(honneJaShadowConfig(activeEnv()).enabled, true);
  assert.equal(honneJaShadowConfig(activeEnv({ LM_HONNE_JA_SHADOW_ENABLED: " TRUE " })).enabled, true);
});

test("a disabled config never plans a generation job even inside a due window", () => {
  const disabled = honneJaShadowConfig({});
  // 2026-07-30T05:00:00Z = 14:00 JST, inside the 12:30 slot window.
  assert.equal(planHonneJaShadowGeneration(disabled, Date.parse("2026-07-30T05:00:00Z")), null);
});

test("an active config requires every input reference explicitly", () => {
  assert.throws(
    () => honneJaShadowConfig(activeEnv({ LM_HONNE_JA_PACK_REF: "" })),
    /LM_HONNE_JA_PACK_REF/,
  );
  assert.throws(
    () => honneJaShadowConfig(activeEnv({ LM_HONNE_JA_MEDIA_REFS: " , " })),
    /LM_HONNE_JA_MEDIA_REFS/,
  );
  assert.throws(
    () => honneJaShadowConfig(activeEnv({ LM_RUNTIME_TENANT_ID: "" })),
    /LM_RUNTIME_TENANT_ID/,
  );
  assert.throws(
    () => honneJaShadowConfig(activeEnv({ LM_HONNE_JA_PUBLICATION_APPROVAL_REF: "" })),
    /LM_HONNE_JA_PUBLICATION_APPROVAL_REF/,
  );
});

test("manual option activates the same reference contract without enabling the scheduler", () => {
  const manual = honneJaShadowConfig(
    activeEnv({ LM_HONNE_JA_SHADOW_ENABLED: "false" }),
    { manual: true },
  );
  assert.equal(manual.enabled, false);
  assert.equal(manual.tenantId, "dais-local");
  assert.equal(manual.packRef, PACK_REF);
});

// ── Slot-locked planning ─────────────────────────────────────────────────────

test("planning inside a slot window builds the exact-slot generation job idempotently", () => {
  const config = honneJaShadowConfig(activeEnv());
  const first = planHonneJaShadowGeneration(config, Date.parse("2026-07-30T03:31:00Z"));
  const second = planHonneJaShadowGeneration(config, Date.parse("2026-07-30T09:00:00Z"));
  assert.ok(first);
  assert.equal(first.capability, "marketing.video.generate");
  assert.equal(first.effect_class, "none");
  assert.equal(first.tenant_id, "dais-local");
  assert.equal(first.input_refs.slot_ref, "schedule-slot://2026-07-30T03:30:00.000Z");
  assert.equal(first.input_refs.pack_ref, PACK_REF);
  assert.deepEqual(first.input_refs.media_refs, [MEDIA_REF_A, MEDIA_REF_B]);
  assert.equal(first.job_id, second.job_id);
});

test("planning before the first slot of the local day yields no job", () => {
  const config = honneJaShadowConfig(activeEnv());
  // 2026-07-30T02:00:00Z = 11:00 JST
  assert.equal(planHonneJaShadowGeneration(config, Date.parse("2026-07-30T02:00:00Z")), null);
});

// ── Shadow hold: publication jobs enqueued, execution held, zero provider calls ──

test("shadow hold enqueues both publication jobs, holds them queued, calls no provider", async () => {
  const config = honneJaShadowConfig(activeEnv());
  const store = fakeDurableStore();
  const holds = [];
  let providerCalls = 0;
  const provider = () => { providerCalls += 1; };

  const { results, hold } = await holdHonneJaShadowPublications(generationReceipt(), config, {
    enqueueJob: store.enqueueJob,
    appendHold: async (record) => { holds.push(record); },
    now: () => "2026-07-30T03:32:00.000Z",
    runDistribution: provider,
  });

  assert.equal(results.length, 2);
  assert.equal(store.jobs.size, 2);
  const jobs = [...store.jobs.values()];
  assert.deepEqual(jobs.map((job) => job.input_refs.platform_ref).sort(), [
    "platform://instagram",
    "platform://tiktok",
  ]);
  assert.ok(jobs.every((job) => job.status === "queued"));
  assert.ok(jobs.every((job) => job.capability === "marketing.video.publish"));
  // Publication jobs exist but not one provider execution happened.
  assert.equal(providerCalls, 0);
  assert.equal(holds.length, 1);
  assert.equal(hold.status, SHADOW_HOLD_STATUS);
  assert.equal(hold.status, "shadow_held");
  assert.equal(hold.kind, "marketing_video_publication_hold");
  assert.equal(hold.product_id, "honne-ai");
  assert.equal(hold.slot, "2026-07-30T03:30:00.000Z");
  assert.deepEqual([...hold.publication_job_ids].sort(), jobs.map((job) => job.job_id).sort());
  assert.equal(hold.held_at, "2026-07-30T03:32:00.000Z");
});

test("shadow hold replay leaves the durable store unchanged and providers untouched", async () => {
  const config = honneJaShadowConfig(activeEnv());
  const store = fakeDurableStore();
  const holds = [];
  const deps = {
    enqueueJob: store.enqueueJob,
    appendHold: async (record) => { holds.push(record); },
    now: () => "2026-07-30T03:32:00.000Z",
  };
  await holdHonneJaShadowPublications(generationReceipt(), config, deps);
  const replay = await holdHonneJaShadowPublications(generationReceipt(), config, deps);
  assert.equal(store.jobs.size, 2);
  assert.ok(replay.results.every(({ created }) => created === false));
  assert.ok([...store.jobs.values()].every((job) => job.status === "queued"));
  // The replay converges without appending a duplicate hold ledger line.
  assert.equal(replay.recorded, false);
  assert.equal(holds.length, 1);
});

test("shadow hold rejects an invalid generation receipt before enqueue or hold", async () => {
  const config = honneJaShadowConfig(activeEnv());
  const store = fakeDurableStore();
  const holds = [];
  await assert.rejects(
    holdHonneJaShadowPublications(
      generationReceipt({ video_sha256: "d".repeat(64) }),
      config,
      { enqueueJob: store.enqueueJob, appendHold: async (record) => { holds.push(record); } },
    ),
    /generation receipt/i,
  );
  assert.equal(store.jobs.size, 0);
  assert.equal(holds.length, 0);
});

test("shadow hold requires the hold sink so held state is always durable", async () => {
  const config = honneJaShadowConfig(activeEnv());
  await assert.rejects(
    holdHonneJaShadowPublications(generationReceipt(), config, {
      enqueueJob: fakeDurableStore().enqueueJob,
    }),
    /hold sink/i,
  );
});

test("appendHonneJaShadowHold persists one JSON line per hold under the tenant data root", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-honne-shadow-"));
  const hold = {
    schema_version: 1,
    kind: "marketing_video_publication_hold",
    status: "shadow_held",
    product_id: "honne-ai",
    creative_id: "HJA-008-aaaaaaaaaaaa",
    slot: "2026-07-30T03:30:00.000Z",
    publication_job_ids: ["a", "b"],
    held_at: "2026-07-30T03:32:00.000Z",
  };
  const first = appendHonneJaShadowHold(hold, {
    dataDir,
    tenantId: "dais-local",
    productId: "honne-ai",
  });
  appendHonneJaShadowHold(hold, { dataDir, tenantId: "dais-local", productId: "honne-ai" });
  const lines = fs.readFileSync(first, "utf8").split(/\r?\n/).filter(Boolean);
  assert.equal(lines.length, 2);
  assert.deepEqual(JSON.parse(lines[0]), hold);
  assert.match(first, /tenants\/dais-local\/marketing\/video-publication-shadow\/honne-ai\/held\.jsonl$/);
});

// ── Seven-cycle status ───────────────────────────────────────────────────────

function completedRow(overrides = {}) {
  return {
    outcome: "completed",
    receipt: generationReceipt(overrides.receipt || {}),
    created_at: overrides.created_at || "2026-07-30T03:30:02.000Z",
  };
}

test("status over an empty history is 0/7 and the gate is not met", () => {
  const status = honneJaShadowStatus([]);
  assert.equal(status.consecutive, 0);
  assert.equal(status.expected, EXPECTED_SHADOW_CYCLES);
  assert.equal(status.expected, 7);
  assert.equal(status.display, "0/7");
  assert.equal(status.gate_met, false);
  assert.deepEqual(status.receipts, []);
});

test("status counts trailing consecutive successful receipts with their timestamps", () => {
  const rows = [1, 2, 3].map((n) => completedRow({
    receipt: {
      slot: `2026-07-2${n}T03:30:00.000Z`,
      generated_at: `2026-07-2${n}T03:30:01.000Z`,
    },
    created_at: `2026-07-2${n}T03:30:02.000Z`,
  }));
  const status = honneJaShadowStatus(rows);
  assert.equal(status.consecutive, 3);
  assert.equal(status.display, "3/7");
  assert.equal(status.gate_met, false);
  assert.deepEqual(status.receipts.map((entry) => entry.slot), [
    "2026-07-21T03:30:00.000Z",
    "2026-07-22T03:30:00.000Z",
    "2026-07-23T03:30:00.000Z",
  ]);
  assert.ok(status.receipts.every((entry) => (
    entry.hook_id === "HJA-008"
    && typeof entry.generated_at === "string"
    && typeof entry.recorded_at === "string"
  )));
});

test("a failure breaks the consecutive streak; only receipts after it count", () => {
  const rows = [
    completedRow(),
    { outcome: "failed", receipt: { error_code: "CAPABILITY_EXECUTION_FAILED" }, created_at: "2026-07-24T03:30:02.000Z" },
    completedRow({ created_at: "2026-07-25T03:30:02.000Z" }),
    completedRow({ created_at: "2026-07-26T03:30:02.000Z" }),
  ];
  const status = honneJaShadowStatus(rows);
  assert.equal(status.consecutive, 2);
  assert.equal(status.display, "2/7");
});

test("an unverifiable completed receipt also breaks the streak", () => {
  const rows = [
    completedRow(),
    { outcome: "completed", receipt: { kind: "runtime_noop" }, created_at: "2026-07-24T03:30:02.000Z" },
    completedRow({ created_at: "2026-07-25T03:30:02.000Z" }),
  ];
  assert.equal(honneJaShadowStatus(rows).consecutive, 1);
});

test("seven or more consecutive successes meet the gate and cap the display", () => {
  const rows = Array.from({ length: 8 }, (_, index) => completedRow({
    created_at: `2026-07-${String(20 + index).padStart(2, "0")}T03:30:02.000Z`,
  }));
  const status = honneJaShadowStatus(rows);
  assert.equal(status.consecutive, 8);
  assert.equal(status.display, "7/7");
  assert.equal(status.gate_met, true);
});

test("status rejects a non-array history", () => {
  assert.throws(() => honneJaShadowStatus(null), /receipts/i);
});
