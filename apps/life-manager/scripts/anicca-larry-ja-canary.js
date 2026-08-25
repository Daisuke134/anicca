#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createContentObjectStore } = require("../lib/content-object-store.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const {
  ACCOUNT_ID,
  INTEGRATION_REF,
  buildMarketingNativeCarouselPublicationJob,
  createMarketingNativeCarouselPublicationLoopAdapter,
  verifyMarketingNativeCarouselPublicationReceipt,
} = require("../lib/marketing-native-carousel-publication-adapter.js");
const {
  buildMarketingLivenessJob,
  executeMarketingLivenessJob,
} = require("../lib/marketing-liveness-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const TENANT = "dais-local";
const PRODUCT = "anicca-ios";
const LOCALE = "ja";
const FORMAT = "larry";
const FORM = "affirmation-carousel";
const LANE = "anicca-larry-ja-instagram";
const TOKEN_REF = "secret://postiz/api-key";
const TELEGRAM_TOKEN_REF = "secret://telegram/bot-token";
const CHAT_REF = "telegram-chat://owner";
const OBJECT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;
const ACCOUNT_REF = "account://instagram/@ani.cca1234";

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function exactInstant(value, label) {
  const text = String(value || "");
  const date = new Date(text);
  if (!Number.isFinite(date.getTime()) || date.toISOString() !== text) {
    throw new Error(`${label} is invalid`);
  }
  return text;
}

function parseArgs(argv = []) {
  if (argv.length === 3 && argv[0] === "run" && argv[1] === "--slot") {
    return { command: "run", slot: exactInstant(argv[2], "Larry JA canary slot") };
  }
  throw new Error("usage: anicca-larry-ja-canary.js run --slot <exact ISO instant>");
}

function parseMediaRefs(value) {
  const raw = String(value || "").trim();
  let values;
  if (raw.startsWith("[")) {
    try { values = JSON.parse(raw); } catch { throw new Error("Larry JA media refs are invalid"); }
  } else values = raw.split(",").map((item) => item.trim()).filter(Boolean);
  if (!Array.isArray(values) || values.length !== 6 || values.some((item) => !OBJECT_REF.test(String(item)))) {
    throw new Error("Larry JA media refs are invalid");
  }
  return values.map(String);
}

function dataDirFrom(env) {
  const raw = required(env.LM_DATA_DIR, "LM_DATA_DIR");
  const dataDir = path.resolve(raw);
  if (!path.isAbsolute(raw) || dataDir === path.parse(dataDir).root) throw new Error("LM_DATA_DIR is invalid");
  return dataDir;
}

function laneConfig(env, parsed, now) {
  const dataDir = dataDirFrom(env);
  const tenantId = required(env.LM_RUNTIME_TENANT_ID, "LM_RUNTIME_TENANT_ID");
  if (tenantId !== TENANT) throw new Error("Larry JA canary tenant is invalid");
  const packRef = required(env.LM_ANICCA_LARRY_JA_PACK_REF, "LM_ANICCA_LARRY_JA_PACK_REF");
  const mediaRefs = parseMediaRefs(env.LM_ANICCA_LARRY_JA_MEDIA_REFS);
  const captionRef = required(env.LM_ANICCA_LARRY_JA_CAPTION_REF, "LM_ANICCA_LARRY_JA_CAPTION_REF");
  const approvalRef = required(env.LM_ANICCA_LARRY_JA_APPROVAL_REF, "LM_ANICCA_LARRY_JA_APPROVAL_REF");
  for (const [ref, label] of [[packRef, "pack"], [captionRef, "caption"], [approvalRef, "approval"]]) {
    if (!OBJECT_REF.test(ref)) throw new Error(`Larry JA ${label} ref is invalid`);
  }
  required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
  required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
  required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID");
  const verificationRef = String(env.LM_ANICCA_LARRY_JA_NATIVE_VERIFICATION_REF || "").trim() || null;
  if (verificationRef && !OBJECT_REF.test(verificationRef)) throw new Error("Larry JA native verification ref is invalid");
  return {
    dataDir,
    tenantId,
    slot: parsed.slot || exactInstant(now(), "Larry JA canary clock"),
    packRef,
    mediaRefs,
    captionRef,
    approvalRef,
    verificationRef,
  };
}

function sha256Json(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function scopedSecretProvider(env, tenantId) {
  return { async get(requestTenantId, ref) {
    if (requestTenantId !== tenantId) throw new Error("Larry JA secret tenant scope mismatch");
    if (ref === TOKEN_REF) return required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
    if (ref === TELEGRAM_TOKEN_REF) return required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
    throw new Error("Larry JA secret reference is not allowed");
  } };
}

async function executeJob(store, job, workerId, handler, execute = executeCapabilityJob) {
  const existing = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (existing) return { created: false, receipt: existing };
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId, leaseSeconds: 300 });
  if (!claim) {
    const retained = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
    if (retained) return { created: false, receipt: retained };
    throw new Error(`Larry JA ${job.capability} job is not claimable`);
  }
  await execute(claim, {
    workerId,
    handlers: { [job.capability]: handler },
    heartbeatJob: (input) => store.heartbeatJob(input),
    completeJob: (input) => store.completeJob(input),
    failJob: (input) => store.failJob(input),
    leaseSeconds: 300,
  });
  const receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (!receipt) {
    const state = await store.readJob({ tenantId: job.tenant_id, jobId: job.job_id });
    const error = new Error(`Larry JA ${job.capability} receipt is unavailable`);
    if (state && state.unknown_effect === true) error.unknownEffect = true;
    throw error;
  }
  return { created: true, receipt };
}

function verifyNativeObject(ref, objectStore, receipt, trustedNow) {
  if (!ref) return false;
  let value;
  try {
    const file = objectStore.resolve(ref);
    value = JSON.parse(fs.readFileSync(file, "utf8"));
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const evidence = String(value.evidence_ref || "");
    if (!OBJECT_REF.test(evidence)) return false;
    objectStore.resolve(evidence);
    const verifiedAt = exactInstant(value.verified_at, "Larry JA native verification verified_at");
    const publishedMs = Date.parse(exactInstant(receipt.published_at, "Larry JA publication published_at"));
    const verifiedMs = Date.parse(verifiedAt);
    const trustedMs = Date.parse(exactInstant(trustedNow, "Larry JA trusted verification clock"));
    return value.schema_version === 1
      && value.kind === "marketing_native_carousel_native_verification"
      && value.status === "verified"
      && value.product_id === PRODUCT
      && value.account_id === ACCOUNT_ID
      && value.integration_ref === INTEGRATION_REF
      && value.public_url === receipt.public_url
      && value.pack_sha256 === receipt.pack_sha256
      && JSON.stringify(value.media_sha256) === JSON.stringify(receipt.media_sha256)
      && value.media_order_sha256 === sha256Json(receipt.media_sha256)
      && value.caption_sha256 === receipt.caption_sha256
      && publishedMs < verifiedMs
      && verifiedMs <= trustedMs;
  } catch {
    return false;
  }
}

function publicationLedgerPath(dataDir, tenantId) {
  return path.join(dataDir, "tenants", encodeURIComponent(tenantId), "marketing", "native-carousel-publication", PRODUCT, "distribution.jsonl");
}

async function runAniccaLarryJaCanary(argv = [], deps = {}) {
  const parsed = parseArgs(argv);
  const env = deps.env || process.env;
  const now = deps.now || (() => new Date().toISOString());
  const trustedNow = exactInstant(now(), "Larry JA canary clock");
  const clock = () => trustedNow;
  const config = laneConfig(env, parsed, clock);
  const objectStore = deps.objectStore || createContentObjectStore({ objectDir: path.join(config.dataDir, "objects") });
  const secretProvider = deps.secretProvider || scopedSecretProvider(env, config.tenantId);
  const store = deps.store || createMarketingLocalLedger({ dataDir: config.dataDir, env, now: clock });
  const publicationJob = buildMarketingNativeCarouselPublicationJob({
    tenantId: config.tenantId,
    productId: PRODUCT,
    formatId: FORMAT,
    form: FORM,
    locale: LOCALE,
    slot: config.slot,
    creativeId: "LARRY-JA-CANARY",
    accountId: ACCOUNT_ID,
    instagramIntegrationRef: INTEGRATION_REF,
    packRef: config.packRef,
    mediaRefs: config.mediaRefs,
    captionRef: config.captionRef,
    approvalRef: config.approvalRef,
    postizTokenRef: TOKEN_REF,
  });
  const queued = await store.enqueueJob({ ...publicationJob, availableAt: trustedNow });
  const publicationAdapter = createMarketingNativeCarouselPublicationLoopAdapter({
    objectStore,
    secretProvider,
    ledgerPath: () => publicationLedgerPath(config.dataDir, config.tenantId),
    ...(deps.runDistribution ? { runDistribution: deps.runDistribution } : {}),
    now: clock,
  });
  const publicationRun = await executeJob(store, publicationJob, "anicca-larry-ja-canary", (job) => publicationAdapter.execute(job), deps.executeCapabilityJob || executeCapabilityJob);
  const publication = publicationRun.receipt;
  if (!verifyMarketingNativeCarouselPublicationReceipt(publication) || publication.provider_reconciled !== true) {
    const error = new Error("Larry JA publication receipt is not reconciled");
    error.unknownEffect = true;
    throw error;
  }
  const publicationResult = { created: queued.created && publicationRun.created, public_url: publication.public_url, provider_post_id: publication.provider_post_id };
  if (!verifyNativeObject(config.verificationRef, objectStore, publication, trustedNow)) {
    return { slot: config.slot, publication: publicationResult, telegram: { created: false, held: true, message_id: null } };
  }
  const telegramJob = buildMarketingLivenessJob({
    tenantId: config.tenantId,
    telegramTokenRef: TELEGRAM_TOKEN_REF,
    telegramChatRef: CHAT_REF,
    payload: { lane: LANE, product: PRODUCT, locale: LOCALE, platform: "instagram", account: ACCOUNT_ID, slot: config.slot, status: "published", public_url: publication.public_url, retry_state: "not_required" },
  });
  const telegramQueued = await store.enqueueJob({ ...telegramJob, availableAt: trustedNow });
  const telegramRun = await executeJob(store, telegramJob, "anicca-larry-ja-canary", (job) => executeMarketingLivenessJob(job, { secretProvider, chatProvider: { get: async (tenantId, ref) => { if (tenantId !== config.tenantId || ref !== CHAT_REF) throw new Error("Larry JA Telegram chat scope mismatch"); return required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID"); } }, sendTelegram: deps.sendTelegram, now: clock }), deps.executeCapabilityJob || executeCapabilityJob);
  return { slot: config.slot, publication: publicationResult, telegram: { created: telegramQueued.created && telegramRun.created, held: false, message_id: telegramRun.receipt.message_id } };
}

if (require.main === module) {
  runAniccaLarryJaCanary(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}

module.exports = { ACCOUNT_ID, INTEGRATION_REF, LANE, parseArgs, runAniccaLarryJaCanary, verifyNativeObject };
