"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { makeInvestmentDryRun, fiveMinuteSlot, runInvestmentDryRun } = require("./investment-dry-run.js");

const state = { uid: "owner-1", lifecycle: "in_review", deployment: "cloud", mode: "paper",
  paused: false, killed: false, core_digest: null, receipt_refs: [],
  alpaca_api_key_ref: null, alpaca_api_secret_ref: null };

test("production fixture is packaged inside the Railway app root with the sealed digest", () => {
  const bytes = fs.readFileSync(path.join(__dirname, "fixtures/investment-preapproval-replay.json"));
  assert.equal(crypto.createHash("sha256").update(bytes).digest("hex"),
    "a123789d7306f1551dc8e8637fc15e2af732f756b57170fe2a1928aeb2375592");
});

test("investment dry-run is disabled by default", async () => {
  let touched = false;
  const run = makeInvestmentDryRun({ listRunnable: async () => { touched = true; } }, {}, { getEnv: () => ({}) });
  assert.deepEqual(await run(new Date()), { status: "disabled", effect_permission: "none" });
  assert.equal(touched, false);
});

test("production entrypoint stays disabled without constructing database dependencies", async () => {
  const previous = process.env.LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED;
  delete process.env.LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED;
  try {
    assert.deepEqual(await runInvestmentDryRun(new Date()), { status: "disabled", effect_permission: "none" });
  } finally {
    if (previous === undefined) delete process.env.LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED;
    else process.env.LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED = previous;
  }
});

test("enabled dry-run writes one effect-none receipt and replay creates no duplicate effect", async () => {
  const completed = [];
  let claimed = false;
  let enqueued;
  const jobs = {
    enqueueJob: async (job) => (enqueued = job, { created: !claimed, job }),
    claimJobs: async () => claimed ? [] : (claimed = true, [{ job_id: enqueued.jobId,
      tenant_id: "owner-1", loop_id: enqueued.loopId, capability: enqueued.capability,
      effect_class: enqueued.effectClass, effect_key: enqueued.effectKey,
      attempt: 1, input_refs: enqueued.inputRefs }]),
    completeJob: async (value) => completed.push(value),
  };
  const run = makeInvestmentDryRun({ listRunnable: async () => [state] }, jobs, {
    getEnv: () => ({ LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED: "true" }),
    fixture: { no_trade: { candidate_ref: "NO_TRADE", gate: "model_no_trade", reason: "No edge" },
      observation: { account: { cash: "100000.00", equity: "100000.00" } } },
    fixtureDigest: "a".repeat(64), workerId: "worker-1",
  });
  const now = new Date("2026-09-06T12:07:59Z");
  const first = await run(now);
  const replay = await run(now);
  assert.equal(first.receipt.effect_permission, "none");
  assert.equal(first.receipt.broker_calls, 0);
  assert.equal(first.receipt.message_calls, 0);
  assert.equal(first.receipt.decision, "NO_TRADE");
  assert.match(first.receipt.core_digest, /^[a-f0-9]{64}$/);
  assert.equal(completed.length, 1);
  assert.deepEqual(replay, { status: "already_processed", effect_permission: "none" });
});

test("five-minute slot is stable", () => {
  assert.equal(fiveMinuteSlot(new Date("2026-09-06T12:09:59Z")), "2026-09-06T12:05:00.000Z");
});

test("an older claimed slot completes with its own immutable lineage", async () => {
  const digest = "b".repeat(64);
  const oldSlot = "2026-09-06T12:00:00.000Z";
  const oldId = crypto.createHash("sha256").update(`owner-1\n${oldSlot}\n${digest}`).digest("hex");
  let completion;
  const jobs = {
    enqueueJob: async (job) => ({ created: true, job }),
    claimJobs: async () => [{ job_id: oldId, tenant_id: "owner-1", loop_id: "investment.cloud",
      capability: "investment.dry-run", effect_class: "none", effect_key: null, attempt: 1,
      input_refs: { investment_state_ref: "investment-state://owner-1",
        fixture_ref: `fixture://alpaca/preapproval-replay/${digest}`,
        schedule_slot_ref: `schedule-slot://${oldSlot}` } }],
    completeJob: async (value) => { completion = value; },
  };
  const run = makeInvestmentDryRun({ listRunnable: async () => [state] }, jobs, {
    getEnv: () => ({ LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED: "true" }), fixtureDigest: digest,
    fixture: { no_trade: { candidate_ref: "NO_TRADE", gate: "model_no_trade", reason: "No edge" },
      observation: { account: { cash: "1.00", equity: "1.00" } } }, workerId: "worker-1",
  });
  const result = await run(new Date("2026-09-06T12:05:00Z"));
  assert.equal(result.receipt.observed_at, oldSlot);
  assert.equal(completion.jobId, oldId);
});

test("claimed job with foreign state lineage fails closed before completion", async () => {
  let completed = false;
  const digest = "c".repeat(64);
  const slot = "2026-09-06T12:00:00.000Z";
  const id = crypto.createHash("sha256").update(`owner-1\n${slot}\n${digest}`).digest("hex");
  const jobs = {
    enqueueJob: async (job) => ({ created: true, job }),
    claimJobs: async () => [{ job_id: id, tenant_id: "owner-1", loop_id: "investment.cloud",
      capability: "investment.dry-run", effect_class: "none", effect_key: null, attempt: 1,
      input_refs: { investment_state_ref: "investment-state://foreign",
        fixture_ref: `fixture://alpaca/preapproval-replay/${digest}`,
        schedule_slot_ref: `schedule-slot://${slot}` } }],
    completeJob: async () => { completed = true; },
  };
  const run = makeInvestmentDryRun({ listRunnable: async () => [state] }, jobs, {
    getEnv: () => ({ LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED: "true" }), fixtureDigest: digest,
    fixture: { no_trade: { candidate_ref: "NO_TRADE", gate: "model_no_trade", reason: "No edge" },
      observation: { account: { cash: "1.00", equity: "1.00" } } }, workerId: "worker-1",
  });
  await assert.rejects(() => run(new Date("2026-09-06T12:05:00Z")), /claimed job invalid/);
  assert.equal(completed, false);
});
