#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { buildRuntimeJob } = require("./runtime-job-store.js");
const { createContentObjectStore, sha256File } = require("./content-object-store.js");
const { resolveRuntimePaths } = require("./runtime-paths.js");

const ADAPTER_ID = "marketing-native-carousel-publication";
const LOOP_ID = "marketing.video.publish";
const CAPABILITY = "marketing.video.publish";
const PRODUCT_ID = "anicca-ios";
const FORMAT_ID = "larry";
const FORM_ID = "affirmation-carousel";
const LOCALE_ID = "ja";
const ACCOUNT_ID = "@ani.cca1234";
const ACCOUNT_REF = "account://instagram/@ani.cca1234";
const INTEGRATION_REF = "integration://postiz/instagram/cmq3sq7mc000eqp0y7azfm8yk";
const PACK_FORMAT_ID = "native-photo-carousel";
const SLIDE_COUNT = 6;
const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const HASH = /^[0-9a-f]{64}$/;
const OBJ = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const DIRECT_POST = /^https:\/\/www\.instagram\.com\/p\/(?=[A-Za-z0-9_-]*[A-Za-z_-])[A-Za-z0-9_-]+\/?$/;
const PROVIDER_ID = /^[A-Za-z0-9._:-]{1,200}$/;
const REF_KEYS = ["account_ref", "approval_ref", "caption_ref", "creative_ref", "form_ref", "format_ref", "instagram_integration_ref", "locale_ref", "media_refs", "pack_ref", "platform_ref", "postiz_token_ref", "product_ref", "slot_ref"];
const EFFECT = /^marketing:carousel:anicca-ios:([A-Za-z0-9][A-Za-z0-9._-]{0,127}):([0-9a-f]{64}):([0-9a-f]{64}):([0-9a-f]{64})$/;

const fail = (message) => { throw new Error(message); };
const text = (value, label) => { const v = String(value == null ? "" : value).trim(); return v || fail(`${label} is required`); };
const objectRef = (value, label) => { const v = String(value || ""); return OBJ.test(v) ? v : fail(`${label} reference is invalid`); };
const objectHash = (value, label) => { const m = OBJ.exec(String(value || "")); return m ? m[1] : fail(`${label} reference is invalid`); };
const instant = (value, label) => { const v = String(value || ""); const d = new Date(v); return Number.isFinite(d.getTime()) && d.toISOString() === v ? v : fail(`${label} is invalid`); };
const digestJson = (value) => crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
const mediaOrderHash = (hashes) => digestJson(hashes);
const mediaRefs = (value) => {
  if (!Array.isArray(value) || value.length !== SLIDE_COUNT) fail("marketing native carousel media references are invalid");
  const refs = value.map((v) => objectRef(v, "marketing native carousel media"));
  if (new Set(refs).size !== refs.length) fail("marketing native carousel media references are invalid");
  return refs;
};

function buildMarketingNativeCarouselPublicationJob(input = {}) {
  const tenantId = text(input.tenantId, "marketing native carousel tenant");
  const productId = text(input.productId, "marketing native carousel product");
  const formatId = text(input.formatId, "marketing native carousel format");
  const form = text(input.form, "marketing native carousel form");
  const locale = text(input.locale, "marketing native carousel locale");
  const creativeId = text(input.creativeId, "marketing native carousel creative");
  const accountId = text(input.accountId, "marketing native carousel account");
  const integrationRef = text(input.instagramIntegrationRef || input.integrationRef, "Instagram integration");
  if (productId !== PRODUCT_ID || formatId !== FORMAT_ID || form !== FORM_ID || locale !== LOCALE_ID || accountId !== ACCOUNT_ID || integrationRef !== INTEGRATION_REF) fail("marketing native carousel lane identity is invalid");
  if (!ID.test(tenantId) || !ID.test(creativeId)) fail("marketing native carousel identity is invalid");
  const slot = instant(input.slot, "marketing native carousel slot");
  const packRef = objectRef(input.packRef, "marketing native carousel pack");
  const media = mediaRefs(input.mediaRefs);
  const captionRef = objectRef(input.captionRef, "marketing native carousel caption");
  const approvalRef = objectRef(input.approvalRef, "marketing native carousel approval");
  const tokenRef = text(input.postizTokenRef, "Postiz token");
  if (!/^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i.test(tokenRef)) fail("Postiz token reference is invalid");
  const packHash = objectHash(packRef, "pack");
  const mediaHashes = media.map((ref) => objectHash(ref, "media"));
  const captionHash = objectHash(captionRef, "caption");
  const effectKey = `marketing:carousel:${PRODUCT_ID}:${creativeId}:${packHash}:${mediaOrderHash(mediaHashes)}:${captionHash}`;
  const inputRefs = {
    product_ref: `product://${PRODUCT_ID}`,
    format_ref: `format://${FORMAT_ID}`,
    form_ref: `form://${FORM_ID}`,
    locale_ref: `locale://${LOCALE_ID}`,
    slot_ref: `schedule-slot://${slot}`,
    creative_ref: `creative://${PRODUCT_ID}/${creativeId}`,
    platform_ref: "platform://instagram",
    account_ref: ACCOUNT_REF,
    instagram_integration_ref: integrationRef,
    pack_ref: packRef,
    media_refs: media,
    caption_ref: captionRef,
    approval_ref: approvalRef,
    postiz_token_ref: tokenRef,
  };
  const jobHash = crypto.createHash("sha256").update(JSON.stringify({ tenant_id: tenantId, effect_key: effectKey })).digest("hex");
  return buildRuntimeJob({ jobId: `marketing-native-carousel-publication:${jobHash}`, tenantId, loopId: LOOP_ID, capability: CAPABILITY, effectClass: "publish", effectKey, inputRefs, maxAttempts: 3 });
}

function normalizeJob(job) {
  const refs = job && job.input_refs;
  if (!refs || typeof refs !== "object" || Array.isArray(refs) || JSON.stringify(Object.keys(refs).sort()) !== JSON.stringify([...REF_KEYS].sort())) fail("marketing native carousel publication job contract is invalid");
  const product = /^product:\/\/(.+)$/.exec(String(refs.product_ref || ""));
  const format = /^format:\/\/(.+)$/.exec(String(refs.format_ref || ""));
  const form = /^form:\/\/(.+)$/.exec(String(refs.form_ref || ""));
  const locale = /^locale:\/\/(.+)$/.exec(String(refs.locale_ref || ""));
  const slot = /^schedule-slot:\/\/(.+)$/.exec(String(refs.slot_ref || ""));
  const creative = /^creative:\/\/(.+)\/([A-Za-z0-9][A-Za-z0-9._-]{0,127})$/.exec(String(refs.creative_ref || ""));
  if (!product || !format || !form || !locale || !slot || !creative || product[1] !== PRODUCT_ID || format[1] !== FORMAT_ID || form[1] !== FORM_ID || locale[1] !== LOCALE_ID || creative[1] !== PRODUCT_ID || refs.platform_ref !== "platform://instagram" || refs.account_ref !== ACCOUNT_REF || refs.instagram_integration_ref !== INTEGRATION_REF) fail("marketing native carousel publication job contract is invalid");
  const input = { tenantId: job.tenant_id, productId: PRODUCT_ID, formatId: FORMAT_ID, form: FORM_ID, locale: LOCALE_ID, slot: slot[1], creativeId: creative[2], accountId: ACCOUNT_ID, instagramIntegrationRef: INTEGRATION_REF, packRef: refs.pack_ref, mediaRefs: refs.media_refs, captionRef: refs.caption_ref, approvalRef: refs.approval_ref, postizTokenRef: refs.postiz_token_ref };
  let expected;
  try { expected = buildMarketingNativeCarouselPublicationJob(input); } catch { fail("marketing native carousel publication job contract is invalid"); }
  if (job.loop_id !== LOOP_ID || job.capability !== CAPABILITY || job.effect_class !== "publish" || job.job_id !== expected.job_id || job.effect_key !== expected.effect_key) fail("marketing native carousel publication job contract is invalid");
  return { ...input, integrationRef: INTEGRATION_REF, packHash: objectHash(input.packRef, "pack"), mediaHashes: input.mediaRefs.map((ref) => objectHash(ref, "media")), captionHash: objectHash(input.captionRef, "caption") };
}

function readJson(file, label) {
  try { const value = JSON.parse(fs.readFileSync(file, "utf8")); return value && typeof value === "object" && !Array.isArray(value) ? value : fail(`${label} is invalid`); } catch (error) { if (error.message === `${label} is invalid`) throw error; fail(`${label} is invalid`); }
}
function assertIntegrity(file, hash, label) {
  if (!file || !fs.statSync(file, { throwIfNoEntry: false })?.isFile()) fail(`${label} object is unavailable`);
  if (sha256File(file) !== hash) fail(`${label} object integrity verification failed`);
}
function assertPack(pack, contract, caption) {
  if (pack.schema_version !== 1 || pack.kind !== "marketing_native_carousel_pack" || pack.product_id !== PRODUCT_ID || pack.locale !== LOCALE_ID || pack.platform !== "instagram" || pack.account_id !== ACCOUNT_ID || pack.renderer_id !== "larry" || pack.format_id !== PACK_FORMAT_ID || pack.form !== FORM_ID || pack.media_type !== "image/jpeg" || pack.slide_count !== SLIDE_COUNT || pack.caption !== caption || !Array.isArray(pack.slides) || pack.slides.length !== SLIDE_COUNT) fail("marketing native carousel pack identity is invalid");
  const ordered = pack.slides.map((slide, i) => {
    if (!slide || slide.position !== i + 1 || slide.role !== (i ? "body" : "hook") || typeof slide.text !== "string" || !OBJ.test(String(slide.media_ref || ""))) fail("marketing native carousel pack slide is invalid");
    return slide.media_ref;
  });
  if (JSON.stringify(ordered) !== JSON.stringify(contract.mediaRefs)) fail("marketing native carousel pack media order mismatch");
}
function assertApproval(approval, contract) {
  const packBound = approval.pack_ref === contract.packRef || approval.pack_sha256 === contract.packHash;
  const refsBound = JSON.stringify(approval.media_refs) === JSON.stringify(contract.mediaRefs);
  const hashesBound = JSON.stringify(approval.media_sha256) === JSON.stringify(contract.mediaHashes)
    && approval.media_order_sha256 === mediaOrderHash(contract.mediaHashes);
  if (approval.schema_version !== 1 || !["marketing_native_carousel_publication_approval", "marketing_native_carousel_approval"].includes(approval.kind) || approval.status !== "approved" || approval.tenant_id !== contract.tenantId || approval.product_id !== PRODUCT_ID || approval.locale !== LOCALE_ID || approval.platform !== "instagram" || approval.account_id !== ACCOUNT_ID || approval.integration_ref !== INTEGRATION_REF || !packBound || (!refsBound && !hashesBound) || approval.caption_sha256 !== contract.captionHash) fail("marketing native carousel approval mismatch");
}
function assertJpeg(file, label) {
  const bytes = fs.readFileSync(file);
  if (bytes.length < 3 || bytes[0] !== 0xff || bytes[1] !== 0xd8 || bytes[2] !== 0xff) fail(`${label} is not JPEG`);
}

function postizEnv(token) {
  const env = {};
  for (const key of ["PATH", "LANG", "LC_ALL", "TMPDIR"]) if (process.env[key] !== undefined) env[key] = process.env[key];
  env.POSTIZ_API_KEY = token;
  return env;
}
function runPostizCarouselProcess(input) {
  const root = path.resolve(__dirname, "../../..");
  const args = [path.join(root, "skills/video/lm-distribution/postiz_video.py")];
  for (const file of input.mediaPaths) args.push("--image", file);
  args.push("--caption-file", input.captionPath, "--integration", input.integrationId, "--platform", "instagram");
  const result = spawnSync(input.python || "python3", args, { cwd: root, env: postizEnv(input.token), encoding: "utf8", timeout: 20 * 60 * 1000, maxBuffer: 4 * 1024 * 1024 });
  if (result.status !== 0) { const error = new Error(`marketing native carousel Postiz failed with exit ${result.status}`); error.unknownEffect = true; throw error; }
  const lines = String(result.stdout || "").split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) { const error = new Error("marketing native carousel Postiz returned invalid JSON"); error.unknownEffect = true; throw error; }
  try { return JSON.parse(lines[0]); } catch { const error = new Error("marketing native carousel Postiz returned invalid JSON"); error.unknownEffect = true; throw error; }
}

function provider(result) {
  const state = result && (result.state || result.status);
  const postId = result && (result.provider_post_id || result.post_id);
  const url = result && (result.public_url || result.post_url);
  const reconciled = result && (result.reconciled === true || result.provider_reconciled === true);
  if (!result || state !== "PUBLISHED" || reconciled !== true || !PROVIDER_ID.test(String(postId || "")) || !DIRECT_POST.test(String(url || ""))) { const error = new Error("marketing native carousel provider result contract mismatch"); error.unknownEffect = true; throw error; }
  return { postId: String(postId), url: String(url) };
}
function verifyMarketingNativeCarouselPublicationReceipt(receipt) {
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt) || receipt.schema_version !== 1 || receipt.kind !== "marketing_native_carousel_distribution" || receipt.status !== "published" || receipt.product_id !== PRODUCT_ID || receipt.format_id !== FORMAT_ID || receipt.form !== FORM_ID || receipt.locale !== LOCALE_ID || receipt.platform !== "instagram" || receipt.account_id !== ACCOUNT_ID || receipt.integration_ref !== INTEGRATION_REF || !ID.test(String(receipt.creative_id || "")) || !HASH.test(String(receipt.pack_sha256 || "")) || !Array.isArray(receipt.media_sha256) || receipt.media_sha256.length !== SLIDE_COUNT || receipt.media_sha256.some((hash) => !HASH.test(String(hash || ""))) || !HASH.test(String(receipt.media_order_sha256 || "")) || receipt.media_order_sha256 !== mediaOrderHash(receipt.media_sha256) || !HASH.test(String(receipt.caption_sha256 || "")) || !PROVIDER_ID.test(String(receipt.provider_post_id || "")) || receipt.provider_reconciled !== true || !DIRECT_POST.test(String(receipt.public_url || ""))) return false;
  try { instant(receipt.published_at, "marketing native carousel receipt published_at"); return true; } catch { return false; }
}
function summary(receipt) {
  if (!verifyMarketingNativeCarouselPublicationReceipt(receipt)) fail("marketing native carousel receipt verification failed");
  return { status: receipt.status, product_id: receipt.product_id, format_id: receipt.format_id, form: receipt.form, locale: receipt.locale, account_id: receipt.account_id, integration_ref: receipt.integration_ref, creative_id: receipt.creative_id, public_url: receipt.public_url, provider_post_id: receipt.provider_post_id, provider_reconciled: true, pack_sha256: receipt.pack_sha256, media_sha256: [...receipt.media_sha256], caption_sha256: receipt.caption_sha256 };
}

function defaultLedgerPath(tenantId, paths) {
  return path.join(paths.dataDir, "tenants", encodeURIComponent(text(tenantId, "tenant")), "marketing", "native-carousel-publication", PRODUCT_ID, "distribution.jsonl");
}
function services(deps = {}) {
  let paths;
  const runtime = () => paths || (paths = resolveRuntimePaths(process.env));
  return { objectStore: deps.objectStore || { resolve: (ref) => createContentObjectStore({ objectDir: runtime().objectDir }).resolve(ref) }, secretProvider: deps.secretProvider, ledgerPath: deps.ledgerPath || ((tenantId) => defaultLedgerPath(tenantId, runtime())), runDistribution: deps.runDistribution || runPostizCarouselProcess, now: deps.now || (() => new Date().toISOString()) };
}
function ledgerFor(s, tenantId) { if (typeof s.ledgerPath === "function") return s.ledgerPath(tenantId, PRODUCT_ID); if (typeof s.ledgerPath === "string" && s.ledgerPath.trim()) return s.ledgerPath; fail("marketing native carousel distribution ledger path is invalid"); }
function appendRow(file, job, receipt) { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.appendFileSync(file, `${JSON.stringify({ effect_key: job.effect_key, job_id: job.job_id, receipt })}\n`, { encoding: "utf8", mode: 0o600 }); fs.chmodSync(file, 0o600); }

async function executeMarketingNativeCarouselPublicationJob(job, deps = {}) {
  const contract = normalizeJob(job);
  const s = services(deps);
  if (!s.objectStore || typeof s.objectStore.resolve !== "function") fail("marketing native carousel object store is required");
  if (!s.secretProvider || typeof s.secretProvider.get !== "function") fail("marketing native carousel secret provider is required");
  const packPath = s.objectStore.resolve(contract.packRef);
  const mediaPaths = contract.mediaRefs.map((ref) => s.objectStore.resolve(ref));
  const captionPath = s.objectStore.resolve(contract.captionRef);
  const approvalPath = s.objectStore.resolve(contract.approvalRef);
  assertIntegrity(packPath, contract.packHash, "marketing native carousel pack");
  mediaPaths.forEach((file, i) => { assertIntegrity(file, contract.mediaHashes[i], `marketing native carousel media ${i + 1}`); assertJpeg(file, `marketing native carousel media ${i + 1}`); });
  assertIntegrity(captionPath, contract.captionHash, "marketing native carousel caption");
  assertIntegrity(approvalPath, objectHash(contract.approvalRef, "approval"), "marketing native carousel approval");
  const caption = fs.readFileSync(captionPath, "utf8");
  assertPack(readJson(packPath, "marketing native carousel pack"), { ...contract, expectedCaption: caption }, caption);
  assertApproval(readJson(approvalPath, "marketing native carousel approval"), contract);
  const token = await s.secretProvider.get(job.tenant_id, contract.postizTokenRef);
  if (typeof token !== "string" || !token.trim()) fail("marketing native carousel Postiz token is invalid");
  let result;
  try { result = await s.runDistribution({ tenantId: job.tenant_id, productId: PRODUCT_ID, formatId: FORMAT_ID, form: FORM_ID, locale: LOCALE_ID, creativeId: contract.creativeId, accountId: ACCOUNT_ID, integrationRef: contract.integrationRef, integrationId: INTEGRATION_REF.split("/").at(-1), packPath, mediaPaths: [...mediaPaths], captionPath, token }); } catch (cause) { const error = new Error(cause && cause.message ? cause.message : String(cause)); error.unknownEffect = true; throw error; }
  const published = provider(result);
  const receipt = { schema_version: 1, kind: "marketing_native_carousel_distribution", status: "published", product_id: PRODUCT_ID, format_id: FORMAT_ID, form: FORM_ID, locale: LOCALE_ID, platform: "instagram", account_id: ACCOUNT_ID, integration_ref: contract.integrationRef, creative_id: contract.creativeId, pack_sha256: contract.packHash, media_sha256: [...contract.mediaHashes], media_order_sha256: mediaOrderHash(contract.mediaHashes), caption_sha256: contract.captionHash, provider_post_id: published.postId, provider_reconciled: true, public_url: published.url, published_at: instant(s.now(), "marketing native carousel publication time") };
  if (!verifyMarketingNativeCarouselPublicationReceipt(receipt)) { const error = new Error("marketing native carousel publication receipt verification failed"); error.unknownEffect = true; throw error; }
  appendRow(ledgerFor(s, job.tenant_id), job, receipt);
  return { receipt, result };
}

function effectParts(key) { const m = EFFECT.exec(text(key, "effect key")); return m || fail("marketing native carousel effect key is invalid"); }
function reconcile(effect, s) {
  const key = effect && (effect.effect_key || effect.effectKey); const file = ledgerFor(s, effect.tenant_id || effect.tenantId); let lines;
  try { lines = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean); } catch (error) { if (error.code === "ENOENT") return { state: "unknown" }; fail("marketing native carousel distribution ledger is invalid"); }
  let malformed = false;
  const parsed = lines.map((line) => { try { return JSON.parse(line); } catch { malformed = true; return null; } });
  if (malformed) return { state: "unknown" };
  const rows = parsed.filter((row) => row && row.effect_key === key);
  if (!rows.length) return { state: "unknown" };
  const receipt = rows.at(-1).receipt || rows.at(-1);
  const m = effectParts(key);
  if (!verifyMarketingNativeCarouselPublicationReceipt(receipt) || receipt.creative_id !== m[1] || receipt.pack_sha256 !== m[2] || receipt.media_order_sha256 !== m[3] || receipt.caption_sha256 !== m[4]) return { state: "unknown" };
  return { state: "present", receipt };
}
function createMarketingNativeCarouselPublicationLoopAdapter(deps = {}) {
  return Object.freeze({ plan: async (input) => [buildMarketingNativeCarouselPublicationJob(input)], execute: (job, extra = {}) => executeMarketingNativeCarouselPublicationJob(job, { ...deps, ...extra }), reconcile: async (effect) => reconcile(effect, services(deps)), verify: verifyMarketingNativeCarouselPublicationReceipt, report: summary });
}

module.exports = { ADAPTER_ID, LOOP_ID, CAPABILITY, PRODUCT_ID, FORMAT_ID, FORM_ID, ACCOUNT_ID, INTEGRATION_REF, buildMarketingNativeCarouselPublicationJob, buildMarketingNativeCarouselJob: buildMarketingNativeCarouselPublicationJob, createMarketingNativeCarouselPublicationLoopAdapter, createMarketingNativeCarouselAdapter: createMarketingNativeCarouselPublicationLoopAdapter, executeMarketingNativeCarouselPublicationJob, executeMarketingNativeCarouselJob: executeMarketingNativeCarouselPublicationJob, runPostizCarouselProcess, safeMarketingNativeCarouselSummary: summary, verifyMarketingNativeCarouselPublicationReceipt, verifyMarketingNativeCarouselReceipt: verifyMarketingNativeCarouselPublicationReceipt };
