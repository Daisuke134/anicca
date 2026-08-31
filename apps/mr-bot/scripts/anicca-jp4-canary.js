#!/usr/bin/env node
"use strict";

const path = require("node:path");
const { createContentObjectStore } = require("../lib/content-object-store.js");
const { buildMarketingLivenessJob, executeMarketingLivenessJob, verifyMarketingLivenessReceipt } = require("../lib/marketing-liveness-adapter.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const { createMarketingVideoPublicationLoopAdapter, verifyMarketingVideoPublicationReceipt } = require("../lib/marketing-video-publication-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const CONFIRMATION = "PROMOTE_ANICCA_JP4_TIKTOK_CANARY";
const TENANT = "dais-local";
const INTEGRATION = "cmn8x8hdv028uqx0y4gdfse5t";
const INTEGRATION_REF = `integration://postiz/tiktok/${INTEGRATION}`;
const APPROVAL_REF = "object://sha256/97f2c5fb2d890b6edef93e7e4c50e69ddaec5d1804b75334e2d5fe1d4599363e";
const VIDEOS = new Set([
  "object://sha256/7e24db967bf76398ff00e4784abe82e48c7c06095f52adbf7461bc65bdaa9ae9",
  "object://sha256/abbbbdea90523e33df5b27fc3bbcf24f7ec21710567b17d5481afecc7c66782a",
  "object://sha256/5639e14832adf38dd249129ed4714cd30f0ade3c2f0808798649bacd1be88a32",
  "object://sha256/35a15c7ce990b1f05b1c8fa1b9665ff552db13f30e3c562b19f0724fac4e9a15",
]);

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function parseArgs(argv) {
  if (argv[0] !== "run" || argv.length !== 5 || argv[1] !== "--tenant" || argv[3] !== "--job-id") {
    throw new Error("usage: anicca-jp4-canary.js run --tenant <id> --job-id <id>");
  }
  return { tenant: required(argv[2], "--tenant"), jobId: required(argv[4], "--job-id") };
}

function resolveTransport(env, deps = {}) {
  const mode = String(env.LM_ANICCA_JP4_CANARY_TRANSPORT || "").trim().toLowerCase();
  if (mode === "postiz") {
    if (env.LM_ANICCA_JP4_CANARY_CONFIRM !== CONFIRMATION || deps.fakeTransport === true) {
      throw new Error("Anicca JP4 Postiz promotion confirmation is invalid");
    }
    return "postiz";
  }
  if (mode !== "fake" && deps.fakeTransport !== true) throw new Error("Anicca JP4 canary requires an explicit fake transport gate");
  return "fake";
}

function assertJp4Job(job, objectStore) {
  const refs = job && job.input_refs || {};
  if (!job || job.tenant_id !== TENANT || job.capability !== "marketing.video.publish" || job.effect_class !== "publish"
    || refs.product_ref !== "product://anicca-ios" || refs.format_ref !== "format://reelclaw-card"
    || refs.form_ref !== "form://nudge-card" || refs.locale_ref !== "locale://ja"
    || refs.platform_ref !== "platform://tiktok" || refs.instagram_profile_ref !== "profile://instagram/unassigned"
    || refs.tiktok_integration_ref !== INTEGRATION_REF || refs.approval_ref !== APPROVAL_REF || !VIDEOS.has(refs.video_ref)) {
    throw new Error("Anicca JP4 canary job is not the approved lane");
  }
  for (const ref of [refs.video_ref, refs.caption_ref, refs.approval_ref]) objectStore.resolve(ref);
  return job;
}

function assertPublication(receipt) {
  if (!verifyMarketingVideoPublicationReceipt(receipt) || receipt.provider_reconciled !== true
    || !/^https:\/\/www\.tiktok\.com\/@anicca\.jp4\/video\/\d+\/?$/.test(receipt.public_url)) {
    throw new Error("Anicca JP4 publication receipt is not reconciled to @anicca.jp4");
  }
  return receipt;
}

async function verifyDirectPublicUrl(url, fetchImpl = globalThis.fetch) {
  if (!/^https:\/\/www\.tiktok\.com\/@anicca\.jp4\/video\/\d+\/?$/.test(url)) {
    throw new Error("Anicca JP4 direct TikTok URL is invalid");
  }
  const response = await fetchImpl(url, { method: "GET", redirect: "follow", headers: { "user-agent": "Mr.bot-canary/1.0" }, signal: AbortSignal.timeout(15_000) });
  if (!response || response.status < 200 || response.status >= 300 || !/^https:\/\/www\.tiktok\.com\/@anicca\.jp4\/video\/\d+\/?$/.test(response.url)) {
    throw new Error("Anicca JP4 direct TikTok URL is not publicly reachable");
  }
  return { status: response.status, url: response.url };
}

function jobInput(job) {
  return { jobId: job.job_id, tenantId: job.tenant_id, loopId: job.loop_id, capability: job.capability, effectClass: job.effect_class, effectKey: job.effect_key, inputRefs: job.input_refs, maxAttempts: job.max_attempts, availableAt: job.available_at };
}

function telegramJob(receipt) {
  return buildMarketingLivenessJob({ tenantId: TENANT, telegramTokenRef: "secret://telegram/bot-token", telegramChatRef: "telegram-chat://owner", payload: {
    lane: "anicca-jp4-canary", product: receipt.product_id, locale: receipt.locale, platform: receipt.platform,
    account: "@anicca.jp4", slot: receipt.slot, status: "published", public_url: receipt.public_url, retry_state: "not_required",
  } });
}

function realExecutor(env) {
  const dataDir = path.resolve(required(env.LM_DATA_DIR, "LM_DATA_DIR"));
  if (env.LM_RUNTIME_TENANT_ID !== TENANT || env.LM_ANICCA_JP4_TIKTOK_INTEGRATION !== INTEGRATION || env.LM_ANICCA_JP4_TIKTOK_INTEGRATION_REF !== INTEGRATION_REF) {
    throw new Error("Anicca JP4 real environment is not the measured route");
  }
  const scoped = (tenant, ref) => { if (tenant !== TENANT) throw new Error("Anicca JP4 tenant scope mismatch"); return ref; };
  const secrets = { get: async (tenant, ref) => {
    const value = scoped(tenant, ref);
    if (value === "secret://postiz/api-key") return required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
    if (value === "secret://telegram/bot-token") return required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
    throw new Error("Anicca JP4 secret reference is not allowed");
  } };
  const publication = createMarketingVideoPublicationLoopAdapter({
    objectStore: createContentObjectStore({ objectDir: path.join(dataDir, "objects") }), secrets,
    secretProvider: secrets,
    integrationProvider: { get: async (tenant, ref) => scoped(tenant, ref) === INTEGRATION_REF ? INTEGRATION : Promise.reject(new Error("Anicca JP4 integration scope mismatch")) },
    ledgerPath: (tenant, product) => path.join(dataDir, "tenants", encodeURIComponent(tenant), "marketing", "video-publication", encodeURIComponent(product), "distribution.jsonl"),
  });
  const chatProvider = { get: async (tenant, ref) => scoped(tenant, ref) === "telegram-chat://owner" ? required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID") : Promise.reject(new Error("Anicca JP4 chat scope mismatch")) };
  return async (job, services) => executeCapabilityJob(job, { ...services, handlers: {
    "marketing.video.publish": (candidate) => publication.execute(candidate),
    "marketing.liveness.telegram": (candidate) => executeMarketingLivenessJob(candidate, { secretProvider: secrets, chatProvider }),
  } });
}

async function run(argv, env = process.env, deps = {}) {
  const { tenant, jobId } = parseArgs(argv);
  if (tenant !== TENANT) throw new Error("Anicca JP4 canary tenant is invalid");
  const transport = resolveTransport(env, deps);
  const store = deps.store || createMarketingLocalLedger({ dataDir: env.LM_DATA_DIR, env });
  const objectStore = deps.objectStore || createContentObjectStore({ objectDir: path.join(path.resolve(required(env.LM_DATA_DIR, "LM_DATA_DIR")), "objects") });
  const workerId = env.LM_ANICCA_JP4_CANARY_WORKER_ID || "anicca-jp4-canary";
  let job = await store.readJob({ tenantId: tenant, jobId });
  assertJp4Job(job, objectStore);
  let receipt = await store.readReceipt({ tenantId: tenant, jobId });
  if (!receipt) {
    if (job.status !== "queued") throw new Error("Anicca JP4 terminal job will not be reposted");
    job = await store.claimJob({ tenantId: tenant, jobId, capability: "marketing.video.publish", workerId, leaseSeconds: 180 });
    if (!job) throw new Error("Anicca JP4 canary did not claim the selected job");
    const execute = deps.execute || (transport === "postiz" ? realExecutor(env) : deps.fakeExecute);
    if (typeof execute !== "function") throw new Error("Anicca JP4 fake executor is required");
    await execute(job, { workerId, heartbeatJob: (input) => store.heartbeatJob(input), completeJob: (input) => store.completeJob(input), failJob: (input) => store.failJob(input), leaseSeconds: 180 });
    receipt = await store.readReceipt({ tenantId: tenant, jobId });
  }
  receipt = assertPublication(receipt);
  const direct = await (transport === "postiz" ? verifyDirectPublicUrl(receipt.public_url) : (deps.verifyDirectPublicUrl || (async (url) => ({ status: 200, url })))(receipt.public_url));
  const message = telegramJob(receipt);
  let messageReceipt = await store.readReceipt({ tenantId: tenant, jobId: message.job_id });
  if (!messageReceipt) {
    await store.enqueueJob(jobInput(message));
    const claimed = await store.claimJob({ tenantId: tenant, jobId: message.job_id, capability: "marketing.liveness.telegram", workerId, leaseSeconds: 180 });
    const execute = deps.execute || (transport === "postiz" ? realExecutor(env) : deps.fakeExecute);
    await execute(claimed, { workerId, heartbeatJob: (input) => store.heartbeatJob(input), completeJob: (input) => store.completeJob(input), failJob: (input) => store.failJob(input), leaseSeconds: 180 });
    messageReceipt = await store.readReceipt({ tenantId: tenant, jobId: message.job_id });
  }
  if (!verifyMarketingLivenessReceipt(messageReceipt) || messageReceipt.public_url !== receipt.public_url) throw new Error("Anicca JP4 Telegram receipt is invalid");
  const replay = await store.enqueueJob(jobInput(job));
  const messageReplay = await store.enqueueJob(jobInput(message));
  return { publication: { job_id: jobId, public_url: receipt.public_url, provider_post_id: receipt.provider_post_id, direct_status: direct.status, replay_created: replay.created }, telegram: { job_id: message.job_id, message_id: messageReceipt.message_id, replay_created: messageReplay.created } };
}

if (require.main === module) run(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { APPROVAL_REF, CONFIRMATION, INTEGRATION, INTEGRATION_REF, VIDEOS, assertJp4Job, parseArgs, resolveTransport, run, verifyDirectPublicUrl };
