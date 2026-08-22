#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { createContentObjectStore } = require("../lib/content-object-store.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const {
  buildMarketingVideoGenerationJob,
  createMarketingVideoGenerationLoopAdapter,
  verifyMarketingVideoGenerationReceipt,
} = require("../lib/marketing-video-generation-adapter.js");
const {
  buildMarketingVideoPublicationJob,
  createMarketingVideoPublicationLoopAdapter,
  verifyMarketingVideoPublicationReceipt,
} = require("../lib/marketing-video-publication-adapter.js");
const { buildMarketingLivenessJob, executeMarketingLivenessJob } = require("../lib/marketing-liveness-adapter.js");
const { marketingVideoDueSlot } = require("../lib/honne-ja-shadow-schedule.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const TENANT = "dais-local";
const PRODUCT = "honne-ai";
const FORMAT = "reelclaw";
const LOCALE = "ja";
const ACCOUNT = "@honnevideo";
const INTEGRATION_ID = "cmnit95mg015rrm0ye5vm8dhl";
const INTEGRATION_REF = `integration://postiz/tiktok/${INTEGRATION_ID}`;
const PRODUCTION_SLOTS = Object.freeze(["08:30", "12:30", "21:30"]);

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function parseArgs(argv) {
  if (argv[0] !== "run" || ![1, 3].includes(argv.length) || (argv.length === 3 && argv[1] !== "--slot")) {
    throw new Error("usage: honne-ja-cycle.js run [--slot <ISO instant>]");
  }
  return argv[1] ? String(argv[2]) : null;
}

function runSlot(slot, nowMs) {
  const value = slot || marketingVideoDueSlot(nowMs, "Asia/Tokyo", PRODUCTION_SLOTS);
  if (!value) throw new Error("honne JA cycle has no due slot yet");
  const slotMs = Date.parse(String(value));
  if (!Number.isFinite(slotMs) || new Date(slotMs).toISOString() !== value) throw new Error("honne JA cycle run timestamp is invalid");
  return value;
}

function historyProvider(dataDir) {
  const file = path.join(dataDir, "marketing", "receipts.jsonl");
  return { async list(scope) {
    if (!fs.existsSync(file)) return [];
    return fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line).receipt)
      .filter((receipt) => receipt && receipt.kind === "marketing_video_artifact"
        && receipt.product_id === scope.productId && receipt.format_id === scope.formatId
        && receipt.locale === scope.locale && verifyMarketingVideoGenerationReceipt(receipt));
  } };
}

async function executeJob(store, job, workerId, handler) {
  const existing = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (existing) return existing;
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId, leaseSeconds: 300 });
  if (!claim) throw new Error(`honne JA ${job.capability} job is not claimable`);
  await executeCapabilityJob(claim, {
    workerId,
    handlers: { [job.capability]: handler },
    heartbeatJob: (input) => store.heartbeatJob(input),
    completeJob: (input) => store.completeJob(input),
    failJob: (input) => store.failJob(input),
    leaseSeconds: 300,
  });
  const receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (!receipt) throw new Error(`honne JA ${job.capability} receipt is unavailable`);
  return receipt;
}

function services(env, dataDir, tenantId) {
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") });
  const scoped = (requestTenantId) => {
    if (requestTenantId !== tenantId) throw new Error("honne JA tenant scope mismatch");
  };
  const secretProvider = { async get(requestTenantId, ref) {
    scoped(requestTenantId);
    if (ref === "secret://postiz/api-key") return required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
    if (ref === "secret://telegram/bot-token") return required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
    throw new Error("honne JA secret reference is not allowed");
  } };
  return {
    publication: createMarketingVideoPublicationLoopAdapter({
      objectStore,
      profileProvider: { get: async () => { throw new Error("honne JA Instagram profile is unassigned"); } },
      secretProvider,
      integrationProvider: { async get(requestTenantId, ref) {
        scoped(requestTenantId);
        if (ref !== INTEGRATION_REF) throw new Error("honne JA TikTok integration scope mismatch");
        return INTEGRATION_ID;
      } },
      ledgerPath: (requestTenantId, productId) => path.join(dataDir, "tenants", encodeURIComponent(requestTenantId), "marketing", "video-publication", encodeURIComponent(productId), "distribution.jsonl"),
    }),
    liveness: (job) => executeMarketingLivenessJob(job, {
      secretProvider,
      chatProvider: { async get(requestTenantId, ref) {
        scoped(requestTenantId);
        if (ref !== "telegram-chat://owner") throw new Error("honne JA Telegram chat scope mismatch");
        return required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID");
      } },
    }),
  };
}

async function runHonneJaCycle(argv, deps = {}) {
  const requestedSlot = parseArgs(argv);
  const env = deps.env || process.env;
  const dataDir = path.resolve(required(deps.dataDir || env.LM_DATA_DIR, "LM_DATA_DIR"));
  const tenantId = required(env.LM_RUNTIME_TENANT_ID, "LM_RUNTIME_TENANT_ID");
  if (tenantId !== TENANT) throw new Error("honne JA cycle tenant is invalid");
  const nowMs = deps.nowMs == null ? Date.now() : deps.nowMs;
  const slot = runSlot(requestedSlot, nowMs);
  const packRef = required(env.LM_HONNE_JA_PACK_REF, "LM_HONNE_JA_PACK_REF");
  const mediaRefs = required(env.LM_HONNE_JA_MEDIA_REFS, "LM_HONNE_JA_MEDIA_REFS").split(",").map((value) => value.trim()).filter(Boolean);
  const approvalRef = required(env.LM_HONNE_JA_PUBLICATION_APPROVAL_REF, "LM_HONNE_JA_PUBLICATION_APPROVAL_REF");
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") });
  const approval = JSON.parse(fs.readFileSync(objectStore.resolve(approvalRef), "utf8"));
  if (approval.scope !== "standing" || approval.product_id !== PRODUCT || approval.locale !== LOCALE || approval.platform !== "tiktok") {
    throw new Error("honne JA cycle approval scope is invalid");
  }
  const store = deps.store || createMarketingLocalLedger({ dataDir });
  const generationJob = buildMarketingVideoGenerationJob({ tenantId, productId: PRODUCT, formatId: FORMAT, locale: LOCALE, slot, packRef, mediaRefs });
  const generationQueued = await store.enqueueJob({ jobId: generationJob.job_id, tenantId, loopId: generationJob.loop_id, capability: generationJob.capability, effectClass: generationJob.effect_class, effectKey: generationJob.effect_key, inputRefs: generationJob.input_refs, maxAttempts: generationJob.max_attempts, availableAt: new Date(nowMs).toISOString() });
  const generationAdapter = createMarketingVideoGenerationLoopAdapter({ dataDir, historyProvider: historyProvider(dataDir), now: () => new Date(nowMs).toISOString() });
  const artifact = await executeJob(store, generationJob, "honne-ja-cycle", (job) => generationAdapter.execute(job));
  const publicationJob = buildMarketingVideoPublicationJob({ tenantId, productId: PRODUCT, formatId: FORMAT, form: artifact.form, locale: LOCALE, slot, creativeId: artifact.creative_id, platform: "tiktok", videoRef: artifact.video_ref, captionRef: artifact.copy_ref, approvalRef, instagramProfileRef: "profile://instagram/unassigned", postizTokenRef: "secret://postiz/api-key", tiktokIntegrationRef: INTEGRATION_REF });
  const publicationQueued = await store.enqueueJob({ jobId: publicationJob.job_id, tenantId, loopId: publicationJob.loop_id, capability: publicationJob.capability, effectClass: publicationJob.effect_class, effectKey: publicationJob.effect_key, inputRefs: publicationJob.input_refs, maxAttempts: publicationJob.max_attempts, availableAt: new Date(nowMs).toISOString() });
  const runtime = services(env, dataDir, tenantId);
  const publication = await executeJob(store, publicationJob, "honne-ja-cycle", (job) => runtime.publication.execute(job));
  if (!verifyMarketingVideoPublicationReceipt(publication) || publication.provider_reconciled !== true || !new RegExp(`^https://www\\.tiktok\\.com/${ACCOUNT}/video/\\d+/?$`).test(publication.public_url)) {
    throw new Error("honne JA publication receipt is not account-bound and reconciled");
  }
  const telegramJob = buildMarketingLivenessJob({ tenantId, telegramTokenRef: "secret://telegram/bot-token", telegramChatRef: "telegram-chat://owner", payload: { lane: "honne-ja", product: PRODUCT, locale: LOCALE, platform: "tiktok", account: ACCOUNT, slot, status: "published", public_url: publication.public_url, retry_state: "not_required" } });
  const telegramQueued = await store.enqueueJob({ jobId: telegramJob.job_id, tenantId, loopId: telegramJob.loop_id, capability: telegramJob.capability, effectClass: telegramJob.effect_class, effectKey: telegramJob.effect_key, inputRefs: telegramJob.input_refs, maxAttempts: telegramJob.max_attempts, availableAt: new Date(nowMs).toISOString() });
  const telegram = await executeJob(store, telegramJob, "honne-ja-cycle", runtime.liveness);
  return { slot, generation: { created: generationQueued.created, creative_id: artifact.creative_id }, publication: { created: publicationQueued.created, public_url: publication.public_url, provider_post_id: publication.provider_post_id }, telegram: { created: telegramQueued.created, message_id: telegram.message_id } };
}

if (require.main === module) runHonneJaCycle(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { PRODUCTION_SLOTS, parseArgs, runHonneJaCycle, runSlot };
