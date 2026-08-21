#!/usr/bin/env node
"use strict";

const {
  buildHonneEnCanaryTelegramJob,
  claimExactCanaryJob,
  createMarketingLocalLedger,
  promoteHonneEnTikTokCanary,
  SHADOW_HOLD_AVAILABLE_AT,
  verifyDirectPublicUrl,
} = require("../lib/marketing-canary.js");
const { verifyMarketingVideoPublicationReceipt } = require("../lib/marketing-video-publication-adapter.js");
const { verifyMarketingLivenessReceipt } = require("../lib/marketing-liveness-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function fakeTransportEnabled(env, deps = {}) {
  const configured = String(env.LM_HONNE_EN_CANARY_TRANSPORT || "").trim().toLowerCase();
  if (configured && configured !== "fake") {
    throw new Error("Honne EN canary transport must be fake; external transport is disabled");
  }
  const executor = deps.executeCapabilityJob;
  const injected = deps.fakeTransport === true
    || deps.transport === "fake"
    || (typeof executor === "function" && (
      executor.fakeTransport === true || executor.transport === "fake"
    ));
  const customExecutor = typeof executor === "function" && executor !== executeCapabilityJob;
  if (customExecutor && !injected) {
    throw new Error("Honne EN canary custom executor requires an explicit fake transport marker");
  }
  const handlers = [
    ...Object.values(deps.handlers || {}),
    ...Object.values(deps.livenessHandlers || {}),
  ];
  if (handlers.some((handler) => typeof handler === "function") && !injected) {
    throw new Error("Honne EN canary handlers require an explicit fake transport marker");
  }
  if (configured === "fake" || injected) return true;
  throw new Error("Honne EN canary requires an explicit fake transport gate");
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

function resolveStore(deps, env) {
  if (deps.store || deps.ledger) return deps.store || deps.ledger;
  return createMarketingLocalLedger({
    dataDir: deps.dataDir || env.LM_DATA_DIR,
    env,
    now: deps.now,
  });
}

async function readReceipt(store, tenantId, jobId) {
  const receipt = await readStoredReceipt(store, tenantId, jobId);
  if (!receipt) throw new Error("Honne EN canary publication receipt is unavailable");
  return assertPublicationReceipt(receipt);
}

function assertPublicationReceipt(receipt) {
  if (!verifyMarketingVideoPublicationReceipt(receipt) || receipt.provider_reconciled !== true) {
    throw new Error("Honne EN canary publication receipt is not reconciled");
  }
  return receipt;
}

async function readStoredReceipt(store, tenantId, jobId) {
  if (!store || typeof store.readReceipt !== "function") {
    throw new Error("Honne EN canary local receipt store is unavailable");
  }
  return store.readReceipt({ tenantId, jobId });
}

async function readStoredJob(store, tenantId, jobId) {
  if (!store || typeof store.readJob !== "function") return null;
  return store.readJob({ tenantId, jobId });
}

async function readTelegramReceipt(store, tenantId, jobId) {
  const receipt = await readStoredReceipt(store, tenantId, jobId);
  return assertTelegramReceipt(receipt);
}

function assertTelegramReceipt(receipt) {
  if (!receipt || !verifyMarketingLivenessReceipt(receipt)) {
    throw new Error("Honne EN canary Telegram receipt is unavailable");
  }
  return receipt;
}

function jobInput(job) {
  return {
    jobId: job.job_id,
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    capability: job.capability,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    inputRefs: job.input_refs,
    maxAttempts: job.max_attempts,
    availableAt: job.available_at,
  };
}

function isPromotedPublicationJob(job) {
  return Boolean(
    job
    && job.status === "queued"
    && job.available_at !== SHADOW_HOLD_AVAILABLE_AT
    && job.capability === "marketing.video.publish"
    && job.effect_class === "publish"
    && job.input_refs
    && job.input_refs.product_ref === "product://honne-ai"
    && job.input_refs.locale_ref === "locale://en"
    && job.input_refs.platform_ref === "platform://tiktok",
  );
}

async function runHonneEnCanary(argv, deps = {}) {
  const args = parseArgs(argv);
  const env = deps.env || process.env;
  fakeTransportEnabled(env, deps);
  const tenantId = args.tenant;
  if (String(env.LM_RUNTIME_TENANT_ID || "").trim() !== tenantId) {
    throw new Error("Honne EN canary tenant does not match worker environment");
  }
  const store = resolveStore(deps, env);
  const workerId = String(env.LM_HONNE_EN_CANARY_WORKER_ID || "honne-en-canary").trim();
  const claim = deps.claimExactCanaryJob || claimExactCanaryJob;
  const execute = deps.executeCapabilityJob || executeCapabilityJob;
  const heartbeat = deps.heartbeatJob || ((input) => store.heartbeatJob(input));
  const complete = deps.completeJob || ((input) => store.completeJob(input));
  const fail = deps.failJob || ((input) => store.failJob(input));
  let publicationJob = await readStoredJob(store, tenantId, args.jobId);
  let publicationReceipt = await readStoredReceipt(store, tenantId, args.jobId);
  let publicationReplay = { created: false };
  if (publicationReceipt) {
    publicationReceipt = assertPublicationReceipt(
      await (deps.readReceipt || readReceipt)(store, tenantId, args.jobId),
    );
  } else {
    if (publicationJob && publicationJob.status !== "queued") {
      throw new Error("Honne EN canary publication receipt is missing; refusing to repost terminal job");
    }
    if (!isPromotedPublicationJob(publicationJob)) {
      await promoteHonneEnTikTokCanary({
        store,
        tenantId,
        jobId: args.jobId,
        confirmation: env.LM_HONNE_EN_CANARY_CONFIRM,
      });
    }
    publicationJob = await claim({
      store,
      tenantId,
      jobId: args.jobId,
      capability: "marketing.video.publish",
      workerId,
      leaseSeconds: 180,
    });
    const handlers = deps.handlers || {};
    await execute(publicationJob, {
      workerId,
      handlers,
      heartbeatJob: heartbeat,
      completeJob: complete,
      failJob: fail,
      leaseSeconds: 180,
    });
    publicationReceipt = await (deps.readReceipt || readReceipt)(store, tenantId, args.jobId);
    publicationReplay = await store.enqueueJob(jobInput(publicationJob));
  }
  const publicUrl = await (deps.verifyDirectPublicUrl || verifyDirectPublicUrl)(
    publicationReceipt.public_url,
    deps.fetchImpl || globalThis.fetch,
  );
  const telegramJob = buildHonneEnCanaryTelegramJob({
    tenantId,
    receipt: publicationReceipt,
  });
  let telegramEnqueued = { created: false };
  let telegramReceipt = await readStoredReceipt(store, tenantId, telegramJob.job_id);
  let telegramReplay = { created: false };
  if (telegramReceipt) {
    telegramReceipt = assertTelegramReceipt(await (deps.readTelegramReceipt || readTelegramReceipt)(
      store,
      tenantId,
      telegramJob.job_id,
    ));
  } else {
    const existingTelegramJob = await readStoredJob(store, tenantId, telegramJob.job_id);
    if (existingTelegramJob && existingTelegramJob.status !== "queued") {
      throw new Error("Honne EN canary Telegram receipt is missing; refusing to resend terminal job");
    }
    telegramEnqueued = await store.enqueueJob(jobInput(telegramJob));
    const telegramClaim = await claim({
      store,
      tenantId,
      jobId: telegramJob.job_id,
      capability: "marketing.liveness.telegram",
      workerId,
      leaseSeconds: 180,
    });
    await execute(telegramClaim, {
      workerId,
      handlers: deps.livenessHandlers || {},
      heartbeatJob: heartbeat,
      completeJob: complete,
      failJob: fail,
      leaseSeconds: 180,
    });
    telegramReceipt = assertTelegramReceipt(await (deps.readTelegramReceipt || readTelegramReceipt)(
      store,
      tenantId,
      telegramJob.job_id,
    ));
    telegramReplay = await store.enqueueJob(jobInput(telegramJob));
  }
  if (telegramReceipt.public_url !== publicationReceipt.public_url) {
    throw new Error("Honne EN canary Telegram URL does not match publication receipt");
  }
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
      replay_created: telegramReplay.created,
    },
  };
}

function fakePublicationReceipt(job) {
  const slotRef = String(job.input_refs && job.input_refs.slot_ref || "");
  const slot = slotRef.startsWith("schedule-slot://")
    ? slotRef.slice("schedule-slot://".length)
    : "2026-08-21T02:00:00.000Z";
  return {
    schema_version: 1,
    kind: "marketing_video_distribution",
    status: "published",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "en",
    slot,
    creative_id: "fake-canary-creative",
    platform: "tiktok",
    video_sha256: "a".repeat(64),
    caption_sha256: "b".repeat(64),
    public_url: "https://www.tiktok.com/@honne_reveal/video/1",
    provider_post_id: "fake-post-1",
    provider_route: "postiz",
    provider_reconciled: true,
    published_at: new Date().toISOString(),
  };
}

function fakeTelegramReceipt() {
  return {
    schema_version: 1,
    kind: "telegram_marketing_liveness",
    lane: "honne-en-canary",
    product: "honne-ai",
    locale: "en",
    platform: "tiktok",
    slot: "2026-08-21T02:00:00.000Z",
    status: "published",
    public_url: "https://www.tiktok.com/@honne_reveal/video/1",
    retry_state: "not_required",
    message_id: 1,
    chat_id_hash: "c".repeat(64),
    sent_at: new Date().toISOString(),
  };
}

async function fakeExecuteCapabilityJob(job, services) {
  await services.completeJob({
    tenantId: job.tenant_id,
    jobId: job.job_id,
    attempt: job.attempt,
    workerId: services.workerId,
    receipt: job.capability === "marketing.video.publish"
      ? fakePublicationReceipt(job)
      : fakeTelegramReceipt(),
  });
}
fakeExecuteCapabilityJob.fakeTransport = true;

async function main(argv = process.argv.slice(2), env = process.env, deps = {}) {
  const configured = String(env.LM_HONNE_EN_CANARY_TRANSPORT || "").trim().toLowerCase();
  if (configured !== "fake") {
    throw new Error(
      "Honne EN canary CLI requires LM_HONNE_EN_CANARY_TRANSPORT=fake; external transport is disabled",
    );
  }
  fakeTransportEnabled(env, deps);
  const result = await runHonneEnCanary(argv, {
    ...deps,
    env,
    fakeTransport: true,
    executeCapabilityJob: deps.executeCapabilityJob || fakeExecuteCapabilityJob,
    verifyDirectPublicUrl: deps.verifyDirectPublicUrl || (async (url) => ({ status: 200, url })),
  });
  if (deps.stdout && typeof deps.stdout.write === "function") {
    deps.stdout.write(`${JSON.stringify(result)}\n`);
  } else {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  }
  return result;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { main, parseArgs, readReceipt, readTelegramReceipt, runHonneEnCanary };
