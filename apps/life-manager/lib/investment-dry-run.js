"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const runtimeJobs = require("./runtime-job-store.js");
const { createInvestmentStateStore } = require("./investment-state-store.js");

const FIXTURE_PATH = path.resolve(__dirname, "fixtures/investment-preapproval-replay.json");
const CAPABILITY = "investment.dry-run";
let pool;

function fiveMinuteSlot(value = new Date()) {
  const milliseconds = value instanceof Date ? value.getTime() : Date.parse(value);
  if (!Number.isFinite(milliseconds)) throw new Error("investment dry-run time invalid");
  return new Date(Math.floor(milliseconds / 300000) * 300000).toISOString();
}

function runReadOnlyCore(fixture) {
  const noTrade = fixture && fixture.no_trade;
  const account = fixture && fixture.observation && fixture.observation.account;
  if (!noTrade || noTrade.candidate_ref !== "NO_TRADE" || noTrade.gate !== "model_no_trade"
    || typeof noTrade.reason !== "string" || !account
    || typeof account.cash !== "string" || typeof account.equity !== "string") {
    throw new Error("investment dry-run fixture invalid");
  }
  return Object.freeze({ decision: noTrade.candidate_ref, gate: noTrade.gate,
    reason: noTrade.reason, cash: account.cash, equity: account.equity });
}

function productionDependencies() {
  const connectionString = String(process.env.LM_RUNTIME_DATABASE_URL || process.env.LM_FEEDBACK_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("investment dry-run database unavailable");
  if (!pool) pool = new (require("pg").Pool)({ connectionString, max: 2 });
  const query = pool.query.bind(pool);
  return {
    stateStore: createInvestmentStateStore({ query }),
    jobs: {
      enqueueJob: (job) => runtimeJobs.enqueueJob(job, { query }),
      claimJobs: (input) => runtimeJobs.claimJobs(input, { query }),
      completeJob: (input) => runtimeJobs.completeJob(input, { query }),
    },
  };
}

function makeInvestmentDryRun(stateStore, jobs, opts = {}) {
  const getEnv = opts.getEnv || (() => process.env);
  const workerId = opts.workerId || `investment-cloud-${process.pid}`;
  return async (now = new Date()) => {
    if (getEnv().LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED !== "true") {
      return { status: "disabled", effect_permission: "none" };
    }
    const states = await stateStore.listRunnable(1);
    if (!states.length) return { status: "no_tenant", effect_permission: "none" };
    const owner = states[0];
    const slot = fiveMinuteSlot(now);
    const fixtureText = opts.fixture ? JSON.stringify(opts.fixture) : fs.readFileSync(FIXTURE_PATH, "utf8");
    const fixture = opts.fixture || JSON.parse(fixtureText);
    const fixtureDigest = opts.fixtureDigest || crypto.createHash("sha256").update(fixtureText).digest("hex");
    const jobId = crypto.createHash("sha256").update(`${owner.uid}\n${slot}\n${fixtureDigest}`).digest("hex");
    await jobs.enqueueJob({ jobId, tenantId: owner.uid, loopId: "investment.cloud",
      capability: CAPABILITY, effectClass: "none", effectKey: null, maxAttempts: 3,
      inputRefs: { investment_state_ref: `investment-state://${owner.uid}`,
        fixture_ref: `fixture://alpaca/preapproval-replay/${fixtureDigest}`,
        schedule_slot_ref: `schedule-slot://${slot}` } });
    const claimed = await jobs.claimJobs({ workerId, capabilities: [CAPABILITY], tenantId: owner.uid,
      limit: 1, leaseSeconds: 180 });
    if (!claimed.length) return { status: "already_processed", effect_permission: "none" };
    const job = claimed[0];
    const refs = job.input_refs;
    const fixtureRef = `fixture://alpaca/preapproval-replay/${fixtureDigest}`;
    const claimedSlot = refs && typeof refs.schedule_slot_ref === "string"
      ? refs.schedule_slot_ref.replace(/^schedule-slot:\/\//, "") : "";
    const expectedJobId = crypto.createHash("sha256")
      .update(`${owner.uid}\n${claimedSlot}\n${fixtureDigest}`).digest("hex");
    if (!refs || refs.fixture_ref !== fixtureRef
      || refs.investment_state_ref !== `investment-state://${owner.uid}`
      || fiveMinuteSlot(claimedSlot) !== claimedSlot || job.job_id !== expectedJobId
      || job.tenant_id !== owner.uid || job.loop_id !== "investment.cloud"
      || job.capability !== CAPABILITY || job.effect_class !== "none" || job.effect_key !== null) {
      throw new Error("investment dry-run claimed job invalid");
    }
    const core = runReadOnlyCore(fixture);
    const coreDigest = crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");
    const receipt = Object.freeze({ effect_permission: "none", broker_calls: 0, message_calls: 0,
      deployment: "cloud", mode: owner.mode, decision: core.decision, gate: core.gate,
      reason: core.reason, cash: core.cash, equity: core.equity, core_digest: coreDigest, fixture_ref: fixtureRef,
      observed_at: claimedSlot });
    await jobs.completeJob({ tenantId: owner.uid, jobId: job.job_id, attempt: job.attempt,
      workerId, receipt });
    return { status: "completed", receipt };
  };
}

async function runInvestmentDryRun(now) {
  if (process.env.LM_INVESTMENT_CLOUD_DRY_RUN_ENABLED !== "true") {
    return { status: "disabled", effect_permission: "none" };
  }
  const { stateStore, jobs } = productionDependencies();
  return makeInvestmentDryRun(stateStore, jobs)(now);
}

module.exports = { CAPABILITY, fiveMinuteSlot, runReadOnlyCore, makeInvestmentDryRun, runInvestmentDryRun };
