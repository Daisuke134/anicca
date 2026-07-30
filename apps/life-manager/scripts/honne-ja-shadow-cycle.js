#!/usr/bin/env node
// honne-ja-shadow-cycle.js — manual one-shot Honne JA SHADOW cycle.
//
// A deliberate manual trigger for exactly one shadow cycle against the real
// durable store, reusing the identical worker execution path the scheduler
// worker uses (createWorkerHandlers + executeCapabilityJob):
//   1. enqueue the slot-locked marketing.video.generate job (idempotent),
//   2. claim + execute it for real (real artifact lineage, durable receipt,
//      no external effect — generation is a no-effect producer),
//   3. enqueue both Instagram/TikTok publication jobs and HOLD them
//      (status shadow_held in the durable hold ledger; the jobs stay queued
//      because no worker is granted marketing.video.publish in shadow).
// It never calls Instagram, TikTok, or Postiz, and it never touches the
// legacy launchd owner. Running this does NOT enable the scheduler.
"use strict";

const os = require("node:os");

const {
  appendHonneJaShadowHold,
  holdHonneJaShadowPublications,
  honneJaShadowConfig,
} = require("../lib/honne-ja-shadow-runtime.js");
const { honneJaDueSlot } = require("../lib/honne-ja-shadow-schedule.js");
const {
  buildMarketingVideoGenerationJob,
} = require("../lib/marketing-video-generation-adapter.js");

function parseArgs(argv) {
  if (argv[0] !== "run") {
    throw new Error("usage: honne-ja-shadow-cycle.js run [--slot <ISO instant>]");
  }
  const args = {};
  for (let index = 1; index < argv.length; index += 2) {
    const flag = String(argv[index] || "");
    const value = argv[index + 1];
    if (
      flag !== "--slot"
      || !value
      || String(value).startsWith("--")
      || Object.hasOwn(args, "slot")
    ) {
      throw new Error("honne JA shadow cycle arguments are invalid");
    }
    args.slot = String(value);
  }
  return args;
}

async function runHonneJaShadowCycle(argv, deps = {}) {
  const args = parseArgs(argv);
  const env = deps.env || process.env;
  const config = honneJaShadowConfig(env, { manual: true });
  const slot = args.slot || honneJaDueSlot(
    deps.nowMs == null ? Date.now() : deps.nowMs,
    config.timeZone,
  );
  if (!slot) {
    throw new Error("no honne JA slot is due yet on the current local day");
  }
  const jobStore = deps.jobStore;
  if (!jobStore) throw new Error("honne JA shadow cycle job store is required");

  // 1. Slot-locked generation job, enqueued idempotently.
  const job = buildMarketingVideoGenerationJob({
    tenantId: config.tenantId,
    productId: config.productId,
    formatId: config.formatId,
    locale: config.locale,
    slot,
    packRef: config.packRef,
    mediaRefs: [...config.mediaRefs],
  });
  const enqueued = await jobStore.enqueueJob({
    jobId: job.job_id,
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    capability: job.capability,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    inputRefs: job.input_refs,
    maxAttempts: job.max_attempts,
  }, jobStore.storeOptions);

  // 2. Claim and execute through the EXACT worker path (the one that produced
  //    the HJA-007 proof): createWorkerHandlers + executeCapabilityJob.
  const workerId = String(env.LM_WORKER_ID || `honne-ja-shadow-cycle-${os.hostname()}`).trim();
  const { createWorkerHandlers, executeCapabilityJob } = require("./runtime-up.js");
  const handlers = deps.createHandlers
    ? deps.createHandlers()
    : createWorkerHandlers(env, ["marketing.video.generate"], { query: jobStore.query });
  const claimed = await jobStore.claimJobs({
    workerId,
    capabilities: ["marketing.video.generate"],
    tenantId: config.tenantId,
    limit: 1,
    leaseSeconds: 300,
  }, jobStore.storeOptions);
  for (const claimedJob of claimed) {
    await executeCapabilityJob(claimedJob, {
      workerId,
      handlers,
      completeJob: jobStore.completeJob,
      failJob: jobStore.failJob,
      storeOptions: jobStore.storeOptions,
    });
  }

  // 3. Durable completed receipt or fail loudly — no completion claim without it.
  const readGenerationReceipt = deps.readGenerationReceipt;
  if (typeof readGenerationReceipt !== "function") {
    throw new Error("honne JA shadow cycle receipt reader is required");
  }
  const receipt = await readGenerationReceipt(config.tenantId, job.job_id);
  if (!receipt) {
    throw new Error("honne JA shadow generation did not complete durably");
  }

  // 4. Publication fanout enqueued and HELD (shadow_held); zero provider calls.
  const appendHold = deps.appendHold || ((hold) => appendHonneJaShadowHold(hold, {
    dataDir: env.LM_DATA_DIR,
    tenantId: config.tenantId,
    productId: config.productId,
  }));
  let ledgerPath = null;
  const { results, hold } = await holdHonneJaShadowPublications(receipt, config, {
    enqueueJob: jobStore.enqueueJob,
    storeOptions: jobStore.storeOptions,
    appendHold: async (record) => {
      ledgerPath = await appendHold(record);
      return ledgerPath;
    },
    now: deps.now,
  });

  return {
    slot,
    generation: {
      job_id: job.job_id,
      created: enqueued.created,
      claimed: claimed.length,
      hook_id: receipt.hook_id,
      creative_id: receipt.creative_id,
      video_ref: receipt.video_ref,
      video_sha256: receipt.video_sha256,
      copy_ref: receipt.copy_ref,
      copy_sha256: receipt.copy_sha256,
      generated_at: receipt.generated_at,
    },
    publications: results.map(({ created, job: publicationJob }) => ({
      job_id: publicationJob.job_id,
      platform: publicationJob.input_refs.platform_ref,
      created,
      status: publicationJob.status,
    })),
    hold: {
      status: hold.status,
      held_at: hold.held_at,
      ledger_path: ledgerPath,
    },
  };
}

async function main() {
  const { Pool } = require("pg");
  const store = require("../lib/runtime-job-store.js");
  const connectionString = String(process.env.LM_RUNTIME_DATABASE_URL || "").trim();
  if (!connectionString) throw new Error("LM_RUNTIME_DATABASE_URL is required");
  const pool = new Pool({ connectionString, max: 2 });
  const opts = { query: pool.query.bind(pool) };
  const jobStore = {
    storeOptions: opts,
    query: opts.query,
    enqueueJob: (input, storeOptions) => store.enqueueJob(input, storeOptions || opts),
    claimJobs: (input, storeOptions) => store.claimJobs(input, storeOptions || opts),
    completeJob: (input, storeOptions) => store.completeJob(input, storeOptions || opts),
    failJob: (input, storeOptions) => store.failJob(input, storeOptions || opts),
  };
  const readGenerationReceipt = async (tenantId, jobId) => {
    const rows = (await opts.query(`
      SELECT r.receipt
      FROM public.lm_runtime_job_receipts r
      WHERE r.tenant_id = $1
        AND r.job_id = $2
        AND r.outcome = 'completed'
      ORDER BY r.attempt DESC
      LIMIT 1
    `, [tenantId, jobId])).rows;
    return rows.length === 1 ? rows[0].receipt : null;
  };
  try {
    const result = await runHonneJaShadowCycle(process.argv.slice(2), {
      jobStore,
      readGenerationReceipt,
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  parseArgs,
  runHonneJaShadowCycle,
};
