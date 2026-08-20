#!/usr/bin/env node
"use strict";

const { Pool } = require("pg");
const {
  buildHonneEnCanaryTelegramJob,
  claimExactCanaryJob,
  promoteHonneEnTikTokCanary,
  verifyDirectPublicUrl,
} = require("../lib/marketing-canary.js");
const { verifyMarketingVideoPublicationReceipt } = require("../lib/marketing-video-publication-adapter.js");
const { verifyMarketingLivenessReceipt } = require("../lib/marketing-liveness-adapter.js");
const {
  enqueueJob,
  heartbeatJob,
  completeJob,
  failJob,
} = require("../lib/runtime-job-store.js");
const {
  createWorkerHandlers,
  executeCapabilityJob,
} = require("./runtime-up.js");

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function parseArgs(argv) {
  if (argv[0] !== "run") {
    throw new Error("usage: honne-en-canary.js run --tenant <id> --job-id <id>");
  }
  const values = {};
  for (let index = 1; index < argv.length; index += 2) {
    const flag = String(argv[index] || "");
    const value = argv[index + 1];
    if (!/^--(tenant|job-id)$/.test(flag) || !value || String(value).startsWith("--")) {
      throw new Error("Honne EN canary arguments are invalid");
    }
    values[flag.slice(2)] = String(value).trim();
  }
  return {
    tenant: required(values.tenant, "--tenant"),
    jobId: required(values["job-id"], "--job-id"),
  };
}

async function readReceipt(query, tenantId, jobId) {
  const result = await query(`
    SELECT r.receipt
    FROM public.lm_runtime_job_receipts r
    WHERE r.tenant_id = $1
      AND r.job_id = $2
      AND r.outcome = 'completed'
    ORDER BY r.attempt DESC
    LIMIT 1
  `, [tenantId, jobId]);
  if (!result || result.rows.length !== 1) throw new Error("Honne EN canary publication receipt is unavailable");
  const receipt = result.rows[0].receipt;
  if (!verifyMarketingVideoPublicationReceipt(receipt) || receipt.provider_reconciled !== true) {
    throw new Error("Honne EN canary publication receipt is not reconciled");
  }
  return receipt;
}

async function readTelegramReceipt(query, tenantId, jobId) {
  const result = await query(`
    SELECT r.receipt
    FROM public.lm_runtime_job_receipts r
    WHERE r.tenant_id = $1
      AND r.job_id = $2
      AND r.outcome = 'completed'
    ORDER BY r.attempt DESC
    LIMIT 1
  `, [tenantId, jobId]);
  if (!result || result.rows.length !== 1 || !verifyMarketingLivenessReceipt(result.rows[0].receipt)) {
    throw new Error("Honne EN canary Telegram receipt is unavailable");
  }
  return result.rows[0].receipt;
}

async function runHonneEnCanary(argv, deps = {}) {
  const args = parseArgs(argv);
  const env = deps.env || process.env;
  const query = deps.query;
  if (typeof query !== "function") throw new Error("Honne EN canary store is unavailable");
  const tenantId = args.tenant;
  if (String(env.LM_RUNTIME_TENANT_ID || "").trim() !== tenantId) {
    throw new Error("Honne EN canary tenant does not match worker environment");
  }
  await promoteHonneEnTikTokCanary({
    query,
    tenantId,
    jobId: args.jobId,
    confirmation: env.LM_HONNE_EN_CANARY_CONFIRM,
  });
  const storeOptions = { query };
  const workerId = String(env.LM_HONNE_EN_CANARY_WORKER_ID || "honne-en-canary").trim();
  const capabilities = ["marketing.video.publish"];
  const jobs = [await (deps.claimExactCanaryJob || claimExactCanaryJob)({
    query,
    tenantId,
    jobId: args.jobId,
    capability: capabilities[0],
    workerId,
    leaseSeconds: 180,
  })];
  const handlers = deps.handlers || createWorkerHandlers(env, capabilities, { query });
  await (deps.executeCapabilityJob || executeCapabilityJob)(jobs[0], {
    workerId,
    handlers,
    heartbeatJob: deps.heartbeatJob || heartbeatJob,
    completeJob: deps.completeJob || completeJob,
    failJob: deps.failJob || failJob,
    storeOptions,
    leaseSeconds: 180,
  });
  const publicationReceipt = await readReceipt(query, tenantId, args.jobId);
  const publicUrl = await (deps.verifyDirectPublicUrl || verifyDirectPublicUrl)(
    publicationReceipt.public_url,
    deps.fetchImpl || globalThis.fetch,
  );
  const publicationReplay = await (deps.enqueueJob || enqueueJob)({
    jobId: jobs[0].job_id,
    tenantId: jobs[0].tenant_id,
    loopId: jobs[0].loop_id,
    capability: jobs[0].capability,
    effectClass: jobs[0].effect_class,
    effectKey: jobs[0].effect_key,
    inputRefs: jobs[0].input_refs,
    maxAttempts: jobs[0].max_attempts,
  }, storeOptions);
  const telegramJob = buildHonneEnCanaryTelegramJob({
    tenantId,
    receipt: publicationReceipt,
  });
  const telegramEnqueued = await (deps.enqueueJob || enqueueJob)({
    jobId: telegramJob.job_id,
    tenantId: telegramJob.tenant_id,
    loopId: telegramJob.loop_id,
    capability: telegramJob.capability,
    effectClass: telegramJob.effect_class,
    effectKey: telegramJob.effect_key,
    inputRefs: telegramJob.input_refs,
    maxAttempts: telegramJob.max_attempts,
  }, storeOptions);
  const livenessCapabilities = ["marketing.liveness.telegram"];
  const livenessJobs = [await (deps.claimExactCanaryJob || claimExactCanaryJob)({
    query,
    tenantId,
    jobId: telegramJob.job_id,
    capability: livenessCapabilities[0],
    workerId,
    leaseSeconds: 180,
  })];
  const livenessHandlers = deps.livenessHandlers || createWorkerHandlers(env, livenessCapabilities, { query });
  await (deps.executeCapabilityJob || executeCapabilityJob)(livenessJobs[0], {
    workerId,
    handlers: livenessHandlers,
    heartbeatJob: deps.heartbeatJob || heartbeatJob,
    completeJob: deps.completeJob || completeJob,
    failJob: deps.failJob || failJob,
    storeOptions,
    leaseSeconds: 180,
  });
  const telegramReceipt = await (deps.readTelegramReceipt || readTelegramReceipt)(
    query,
    tenantId,
    telegramJob.job_id,
  );
  if (telegramReceipt.public_url !== publicationReceipt.public_url) {
    throw new Error("Honne EN canary Telegram URL does not match publication receipt");
  }
  const replay = await (deps.enqueueJob || enqueueJob)({
    jobId: telegramJob.job_id,
    tenantId: telegramJob.tenant_id,
    loopId: telegramJob.loop_id,
    capability: telegramJob.capability,
    effectClass: telegramJob.effect_class,
    effectKey: telegramJob.effect_key,
    inputRefs: telegramJob.input_refs,
    maxAttempts: telegramJob.max_attempts,
  }, storeOptions);
  return {
    publication: {
      job_id: args.jobId,
      status: publicationReceipt.status,
      public_url: publicationReceipt.public_url,
      public_url_status: publicUrl.status,
      provider_post_id: publicationReceipt.provider_post_id,
      provider_reconciled: publicationReceipt.provider_reconciled,
      replay_created: publicationReplay.created,
    },
    telegram: {
      job_id: telegramJob.job_id,
      created: telegramEnqueued.created,
      message_id: telegramReceipt.message_id,
      replay_created: replay.created,
    },
  };
}

async function main() {
  const env = process.env;
  const connectionString = required(env.LM_RUNTIME_DATABASE_URL, "LM_RUNTIME_DATABASE_URL");
  const pool = new Pool({ connectionString, max: 2 });
  try {
    const result = await runHonneEnCanary(process.argv.slice(2), {
      env,
      query: pool.query.bind(pool),
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

module.exports = { parseArgs, readReceipt, readTelegramReceipt, runHonneEnCanary };
