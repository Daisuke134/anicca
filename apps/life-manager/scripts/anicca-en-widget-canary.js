#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const { createContentObjectStore } = require("../lib/content-object-store.js");
const { createMarketingLocalLedger } = require("../lib/marketing-local-ledger.js");
const { createMarketingLaneManifest, isMarketingLaneManifest, writeMarketingLaneManifest } = require("../lib/marketing-lane-manifest.js");
const {
  buildMarketingVideoPublicationJob,
  createMarketingVideoPublicationLoopAdapter,
  runDistributionProcess,
  verifyMarketingVideoPublicationReceipt,
} = require("../lib/marketing-video-publication-adapter.js");
const { buildMarketingLivenessJob, executeMarketingLivenessJob } = require("../lib/marketing-liveness-adapter.js");
const { executeCapabilityJob } = require("./runtime-up.js");

const TENANT = "dais-local";
const PRODUCT = "anicca-ios";
const LOCALE = "en";
const PLATFORM = "instagram";
const ACCOUNT_ID = "@anicca.en";
const MANIFEST_ACCOUNT = "anicca-ios-en-widget-instagram";
const PROFILE_REF = "profile://instagram/anicca.en";
const INTEGRATION_REF = "integration://postiz/instagram/cmn8y95rg02d2qx0y09bbk5pb";
const INTEGRATION_ID = "cmn8y95rg02d2qx0y09bbk5pb";
const RENDERER = "reelclaw-widget";
const FORMAT = "reelclaw-widget";
const PACK_FORMAT = "widget-demo-reel";
const FORM = "lockscreen-affirmation-widget";
const LANE = "anicca-en-widget-instagram";
const CREATIVE_ID = "EN-WIDGET-CANARY-98f4ce8c607a";
const TOKEN_REF = "secret://postiz/api-key";
const TELEGRAM_TOKEN_REF = "secret://telegram/bot-token";
const CHAT_REF = "telegram-chat://owner";
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const DIRECT_REEL = /^https:\/\/www\.instagram\.com\/reel\/(?=[A-Za-z0-9_-]*[A-Za-z_-])[A-Za-z0-9_-]+\/?$/;

const required = (value, label) => {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
};
const exactInstant = (value, label) => {
  const text = String(value || "");
  const date = new Date(text);
  if (!Number.isFinite(date.getTime()) || date.toISOString() !== text) throw new Error(`${label} is invalid`);
  return text;
};
const objectRef = (value, label) => {
  const text = String(value || "");
  if (!OBJECT_REF.test(text)) throw new Error(`${label} reference is invalid`);
  return text;
};
const hashRef = (value) => objectRef(value, "content").slice(-64);
const directReel = (value) => DIRECT_REEL.test(String(value || ""));
const sha256Bytes = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");

function htmlText(value) {
  return String(value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#39;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/\s+/g, " ")
    .trim();
}

function visibleCaption(html) {
  const dataTest = /data-testid=["']caption["'][^>]*>([\s\S]*?)<\/[^>]+>/i.exec(html);
  if (dataTest) return htmlText(dataTest[1]);
  const captionDiv = /<div[^>]+class=["'][^"']*\bCaption\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/i.exec(html);
  if (captionDiv) {
    const withoutUsername = captionDiv[1]
      .replace(/<a[^>]+class=["'][^"']*\bCaptionUsername\b[^"']*["'][^>]*>[\s\S]*?<\/a>/i, "")
      .replace(/^(?:\s*<br\s*\/?>\s*)+/i, "");
    return htmlText(withoutUsername);
  }
  const meta = /<meta[^>]+(?:property|name)=["']og:description["'][^>]+content=["']([^"']*)["'][^>]*>/i.exec(html);
  return meta ? htmlText(meta[1]) : "";
}

function embedVideoUrl(html) {
  if (!/GraphVideo/i.test(html)) return null;
  let decoded = String(html || "");
  for (let i = 0; i < 3; i += 1) decoded = decoded.replace(/\\"/g, '"').replace(/\\\//g, "/");
  const match = /["']video_url["']\s*:\s*["']([^"']+)["']/i.exec(decoded);
  if (!match) return null;
  try {
    const parsed = new URL(match[1]);
    if (parsed.protocol !== "https:" || !/(^|\.)cdninstagram\.com$|(^|\.)fbcdn\.net$/i.test(parsed.hostname)) return null;
    return parsed.toString();
  } catch { return null; }
}

function probeVideo(file, ffprobeBin = "ffprobe") {
  const result = spawnSync(ffprobeBin, ["-v", "error", "-print_format", "json", "-show_streams", "-show_format", file], {
    encoding: "utf8", maxBuffer: 2 * 1024 * 1024,
  });
  if (!result || result.status !== 0) return null;
  try {
    const parsed = JSON.parse(result.stdout || "{}");
    const stream = (parsed.streams || []).find((item) => item.codec_type === "video");
    const duration = Number(stream && (stream.duration || parsed.format && parsed.format.duration));
    const width = Number(stream && stream.width);
    const height = Number(stream && stream.height);
    if (!stream || !Number.isFinite(duration) || duration <= 0 || !Number.isSafeInteger(width) || width < 2 || !Number.isSafeInteger(height) || height < 2) return null;
    return { duration, aspect: width / height, width, height };
  } catch { return null; }
}

function compareNativeVideo(nativePath, approvedPath, options = {}) {
  const native = probeVideo(nativePath, options.ffprobeBin || "ffprobe");
  const approved = probeVideo(approvedPath, options.ffprobeBin || "ffprobe");
  if (!native || !approved) return false;
  const durationDelta = Math.abs(native.duration - approved.duration);
  if (durationDelta > 0.25) return false;
  if (Math.abs(native.aspect - approved.aspect) > 0.03) return false;
  const width = approved.width;
  const height = approved.height;
  const expectedFrames = Math.max(1, Math.ceil(Math.max(native.duration, approved.duration) * 2));
  const pad = (label) => `[${label}:v]fps=2,setpts=PTS-STARTPTS,scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p`;
  const filter = `${pad("0")} [native];${pad("1")} [approved];[native][approved]ssim=stats_file=-`;
  const result = spawnSync(options.ffmpegBin || "ffmpeg", ["-loglevel", "error", "-i", nativePath, "-i", approvedPath, "-filter_complex", filter, "-frames:v", String(expectedFrames), "-f", "null", "-"], {
    encoding: "utf8", maxBuffer: 2 * 1024 * 1024,
  });
  const output = `${result && result.stdout || ""}\n${result && result.stderr || ""}`;
  const scores = [...output.matchAll(/All:([0-9.]+)/g)].map((match) => Number(match[1]));
  const comparedFrames = (output.match(/\bn:\d+/g) || []).length;
  return Boolean(result && result.status === 0 && comparedFrames >= expectedFrames - 1 && scores.length >= expectedFrames - 1 && scores.every((score) => score >= 0.945));
}

function parseArgs(argv = []) {
  if (argv.length === 3 && argv[0] === "run" && argv[1] === "--slot") {
    return { command: "run", slot: exactInstant(argv[2], "Anicca EN widget canary slot") };
  }
  throw new Error("usage: anicca-en-widget-canary.js run --slot <exact ISO instant>");
}

function laneConfig(env, parsed) {
  const rawDataDir = required(env.LM_DATA_DIR, "LM_DATA_DIR");
  const dataDir = path.resolve(rawDataDir);
  if (!path.isAbsolute(rawDataDir) || dataDir === path.parse(dataDir).root) throw new Error("LM_DATA_DIR is invalid");
  const tenantId = required(env.LM_RUNTIME_TENANT_ID, "LM_RUNTIME_TENANT_ID");
  if (tenantId !== TENANT) throw new Error("Anicca EN widget canary tenant is invalid");
  const config = {
    dataDir,
    tenantId,
    slot: parsed.slot,
    packRef: objectRef(env.LM_ANICCA_EN_WIDGET_PACK_REF, "Anicca EN widget pack"),
    videoRef: objectRef(env.LM_ANICCA_EN_WIDGET_VIDEO_REF, "Anicca EN widget video"),
    captionRef: objectRef(env.LM_ANICCA_EN_WIDGET_CAPTION_REF, "Anicca EN widget caption"),
    approvalRef: objectRef(env.LM_ANICCA_EN_WIDGET_APPROVAL_REF, "Anicca EN widget approval"),
    verificationRef: String(env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF || "").trim() || null,
  };
  if (config.verificationRef) objectRef(config.verificationRef, "Anicca EN widget native verification");
  return config;
}

function readJson(store, ref, label) {
  try {
    const file = store.resolve(ref);
    return { file, value: JSON.parse(fs.readFileSync(file, "utf8")) };
  } catch {
    throw new Error(`${label} object is invalid`);
  }
}

function verifyInputs(config, store) {
  const packObject = readJson(store, config.packRef, "Anicca EN widget pack");
  const approvalObject = readJson(store, config.approvalRef, "Anicca EN widget approval");
  store.resolve(config.videoRef);
  const captionPath = store.resolve(config.captionRef);
  const pack = packObject.value;
  const approval = approvalObject.value;
  const media = pack && Array.isArray(pack.media) && pack.media.length === 1 ? pack.media[0] : null;
  if (
    !pack || typeof pack !== "object" || Array.isArray(pack)
    || pack.schema_version !== 1 || pack.kind !== "marketing_video_asset_pack"
    || pack.product_id !== PRODUCT || pack.locale !== LOCALE || pack.platform !== PLATFORM
    || pack.account_id !== ACCOUNT_ID || pack.integration_id !== INTEGRATION_ID
    || pack.renderer_id !== RENDERER || pack.format_id !== PACK_FORMAT || pack.form !== FORM
    || pack.caption_ref !== config.captionRef || typeof pack.caption !== "string"
    || !media || typeof media !== "object" || media.video_ref !== config.videoRef
  ) throw new Error("Anicca EN widget pack identity mismatch");
  if (!Buffer.from(pack.caption, "utf8").equals(fs.readFileSync(captionPath))) throw new Error("Anicca EN widget pack caption mismatch");
  const visualEvidenceRef = objectRef(pack.visual_evidence_ref, "Anicca EN widget visual evidence");
  store.resolve(visualEvidenceRef);
  const approvalAccount = Object.hasOwn(approval || {}, "account_id") ? approval.account_id : approval && approval.account;
  if (
    !approval || typeof approval !== "object" || Array.isArray(approval)
    || approval.schema_version !== 1 || approval.kind !== "marketing_video_publication_approval"
    || approval.status !== "approved" || approval.tenant_id !== TENANT || approval.product_id !== PRODUCT
    || approval.format_id !== FORMAT || approval.form !== FORM || approval.locale !== LOCALE
    || approval.platform !== PLATFORM || approvalAccount !== ACCOUNT_ID
    || approval.integration_ref !== INTEGRATION_REF || approval.pack_ref !== config.packRef
    || approval.creative_id !== CREATIVE_ID || approval.video_sha256 !== hashRef(config.videoRef)
    || approval.caption_sha256 !== hashRef(config.captionRef)
  ) throw new Error("Anicca EN widget approval mismatch");
  return { caption: pack.caption, visualEvidenceRef };
}

async function executeJob(store, job, handler, execute = executeCapabilityJob) {
  let receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (receipt) return { created: false, receipt };
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId: "anicca-en-widget-canary", leaseSeconds: 300 });
  if (!claim) {
    receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
    if (receipt) return { created: false, receipt };
    const state = await store.readJob({ tenantId: job.tenant_id, jobId: job.job_id });
    const error = new Error(`Anicca EN widget ${job.capability} job is not claimable`);
    if (state && state.unknown_effect === true) error.unknownEffect = true;
    throw error;
  }
  await execute(claim, {
    workerId: "anicca-en-widget-canary",
    handlers: { [job.capability]: handler },
    heartbeatJob: (input) => store.heartbeatJob(input),
    completeJob: (input) => store.completeJob(input),
    failJob: (input) => store.failJob(input),
    leaseSeconds: 300,
  });
  receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (!receipt) {
    const state = await store.readJob({ tenantId: job.tenant_id, jobId: job.job_id });
    const error = new Error(`Anicca EN widget ${job.capability} receipt is unavailable`);
    if (state && state.unknown_effect === true) error.unknownEffect = true;
    throw error;
  }
  return { created: true, receipt };
}

async function verifyNativeObject(ref, store, config, receipt, trustedNow, options = {}) {
  if (!ref) return false;
  try {
    const verificationObject = readJson(store, ref, "Anicca EN widget native verification").value;
    const account = Object.hasOwn(verificationObject || {}, "account_id") ? verificationObject.account_id : verificationObject && verificationObject.account;
    const evidenceRef = objectRef(verificationObject && verificationObject.evidence_ref, "Anicca EN widget native evidence");
    const evidence = readJson(store, evidenceRef, "Anicca EN widget native evidence").value;
    const nativeVideoRef = objectRef(evidence && evidence.native_video_ref, "Anicca EN widget native video");
    const nativeContactSheetRef = objectRef(evidence && evidence.native_contact_sheet_ref, "Anicca EN widget native contact sheet");
    store.resolve(nativeVideoRef);
    store.resolve(nativeContactSheetRef);
    const verifiedAt = exactInstant(verificationObject.verified_at, "Anicca EN widget native verification verified_at");
    const publishedAt = exactInstant(receipt.published_at, "Anicca EN widget publication published_at");
    const observedAt = exactInstant(evidence.observed_at, "Anicca EN widget native evidence observed_at");
    if (!(verificationObject && typeof verificationObject === "object" && !Array.isArray(verificationObject)
      && verificationObject.schema_version === 1 && verificationObject.kind === "marketing_video_native_verification"
      && verificationObject.status === "verified" && verificationObject.product_id === PRODUCT && account === ACCOUNT_ID
      && verificationObject.integration_ref === INTEGRATION_REF && verificationObject.public_url === receipt.public_url
      && verificationObject.pack_sha256 === hashRef(config.packRef) && verificationObject.video_sha256 === hashRef(config.videoRef)
      && verificationObject.caption_sha256 === hashRef(config.captionRef)
      && evidence && typeof evidence === "object" && !Array.isArray(evidence)
      && evidence.schema_version === 1 && evidence.kind === "marketing_video_native_evidence"
      && evidence.status === "verified" && evidence.platform === PLATFORM
      && evidence.public_url === receipt.public_url && evidence.account_id === ACCOUNT_ID
      && evidence.integration_ref === INTEGRATION_REF && evidence.caption === config.packCaption
      && evidence.caption_sha256 === hashRef(config.captionRef) && evidence.video_sha256 === hashRef(config.videoRef)
      && evidence.observation_method === "instagram-captioned-embed+native-video-frame-comparison"
      && evidence.source_contact_sheet_ref === config.visualEvidenceRef
      && !["account_match", "caption_match", "content_match"].some((key) => Object.hasOwn(evidence, key)))) return false;
    const fetchImpl = options.fetchImpl || globalThis.fetch;
    if (typeof fetchImpl !== "function") return false;
    const embedUrl = `${receipt.public_url}embed/captioned/`;
    const embedResponse = await fetchImpl(embedUrl, { method: "GET", redirect: "follow" });
    if (!embedResponse || Number(embedResponse.status) !== 200 || typeof embedResponse.text !== "function") return false;
    if (embedResponse.url && embedResponse.url !== embedUrl) return false;
    const html = await embedResponse.text();
    const ownerPath = ACCOUNT_ID.slice(1);
    const ownerLink = [...String(html).matchAll(/<a\b[^>]*>[\s\S]*?<\/a>/gi)].some(([anchor]) => {
      const classMatch = /class=["']([^"']*)["']/i.exec(anchor);
      const hrefMatch = /href=["']([^"']+)["']/i.exec(anchor);
      if (!classMatch || !hrefMatch || !classMatch[1].split(/\s+/).includes("CaptionUsername")) return false;
      try {
        const parsed = new URL(hrefMatch[1]);
        return parsed.protocol === "https:" && parsed.hostname === "www.instagram.com"
          && !parsed.port && !parsed.username && !parsed.password && !parsed.hash
          && parsed.pathname.replace(/^\/+|\/+$/g, "") === ownerPath;
      } catch { return false; }
    });
    if (!ownerLink) return false;
    if (visibleCaption(html) !== htmlText(config.packCaption)) return false;
    const videoUrl = embedVideoUrl(html);
    if (!videoUrl) return false;
    const mediaResponse = await fetchImpl(videoUrl, { method: "GET", redirect: "follow" });
    if (!mediaResponse || Number(mediaResponse.status) !== 200 || typeof mediaResponse.arrayBuffer !== "function") return false;
    if (mediaResponse.url && mediaResponse.url !== videoUrl) return false;
    const media = Buffer.from(await mediaResponse.arrayBuffer());
    if (media.length < 1 || media.length > 50 * 1024 * 1024 || sha256Bytes(media) !== hashRef(evidence.native_video_ref)) return false;
    const nativePath = store.resolve(nativeVideoRef);
    const approvedPath = store.resolve(config.videoRef);
    const comparator = options.comparator || compareNativeVideo;
    if (typeof comparator !== "function" || !(await comparator(nativePath, approvedPath))) return false;
    return Date.parse(publishedAt) < Date.parse(observedAt)
      && Date.parse(observedAt) <= Date.parse(verifiedAt)
      && Date.parse(verifiedAt) <= Date.parse(exactInstant(trustedNow, "Anicca EN widget trusted clock"));
  } catch {
    return false;
  }
}

function publicationLedgerPath(dataDir, tenantId) {
  return path.join(dataDir, "tenants", encodeURIComponent(tenantId), "marketing", "video-publication", PRODUCT, "distribution.jsonl");
}

function controlPaths(dataDir) {
  const directory = path.join(dataDir, "marketing");
  return { directory, manifest: path.join(directory, "lane-manifest.json"), fence: path.join(directory, "publication-effect-fence.json") };
}

function readControl(file, label) {
  const stat = fs.statSync(file, { throwIfNoEntry: false });
  if (!stat || !stat.isFile() || (stat.mode & 0o777) !== 0o600) throw new Error(`${label} is unavailable`);
  const bytes = fs.readFileSync(file);
  let value;
  try { value = JSON.parse(bytes.toString("utf8")); } catch { throw new Error(`${label} is invalid`); }
  return { bytes, mode: stat.mode & 0o777, value };
}

function atomicBytes(file, bytes, mode = 0o600) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.tmp-${process.pid}-${Date.now()}`;
  const descriptor = fs.openSync(temporary, "wx", mode);
  try { fs.writeSync(descriptor, bytes); fs.fsyncSync(descriptor); } finally { fs.closeSync(descriptor); }
  fs.renameSync(temporary, file);
  fs.chmodSync(file, mode);
  const directory = fs.openSync(path.dirname(file), fs.constants.O_RDONLY);
  try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
}

function restoreControls(paths, saved) {
  let failure;
  try { atomicBytes(paths.manifest, saved.manifest.bytes, saved.manifest.mode); } catch (error) { failure = error; }
  try { atomicBytes(paths.fence, saved.fence.bytes, saved.fence.mode); } catch (error) { failure ||= error; }
  if (failure) throw failure;
}

function armControls(config, job) {
  const paths = controlPaths(config.dataDir);
  const manifest = readControl(paths.manifest, "Anicca EN widget lane manifest");
  const fence = readControl(paths.fence, "Anicca EN widget publication fence");
  if (
    !isMarketingLaneManifest(manifest.value) || manifest.value.tenant_id !== TENANT
    || fence.value.schema_version !== 1 || fence.value.state !== "closed"
  ) throw new Error("Anicca EN widget publication controls are not closed");
  const targets = manifest.value.lanes.filter((lane) => (
    lane.tenant_id === TENANT && lane.product_id === "anicca" && lane.locale === LOCALE
    && lane.platform === PLATFORM && lane.account === MANIFEST_ACCOUNT
    && lane.profile === ACCOUNT_ID && lane.integration_id === INTEGRATION_ID
  ));
  if (targets.length !== 1 || manifest.value.lanes.some((lane) => lane.production_armed !== false)) throw new Error("Anicca EN widget target lane is not default-off");
  const target = targets[0];
  if (
    target.provider !== "postiz" || target.disabled !== false || target.lane_state !== "default-off"
    || target.account !== MANIFEST_ACCOUNT || target.profile !== ACCOUNT_ID
    || target.disposition !== "target" || target.production_armed !== false || target.owner !== "life-manager"
    || target.renderer !== RENDERER || target.format !== PACK_FORMAT || target.canary_state !== "pack-ready"
    || !Number.isSafeInteger(target.target_daily_limit) || target.target_daily_limit < 1
  ) throw new Error("Anicca EN widget target lane identity is invalid");
  const rows = manifest.value.lanes.map((lane) => ({
    ...lane,
    verified: true,
    ...(lane.integration_id === INTEGRATION_ID ? { lane_state: "production-armed", production_armed: true } : { production_armed: false }),
  }));
  const armed = createMarketingLaneManifest({
    tenant_id: TENANT,
    integrations: rows,
    holds: manifest.value.holds.map((hold) => ({ ...hold, verified: true })),
  }, { tenantId: TENANT, assignments: rows.map((row) => ({ ...row })) });
  const saved = { paths, manifest, fence };
  try {
    writeMarketingLaneManifest(armed, { dataDir: config.dataDir });
    atomicBytes(paths.fence, Buffer.from(`${JSON.stringify({ schema_version: 1, state: "open", allowed_effect_key: job.effect_key, reason: "one Anicca EN widget canary" })}\n`), fence.mode);
  } catch (error) {
    try { restoreControls(paths, saved); } catch (restoreError) { error.unknownEffect = true; error.cause = restoreError; }
    throw error;
  }
  return saved;
}

async function runAniccaEnWidgetCanary(argv = [], deps = {}) {
  const parsed = parseArgs(argv);
  const env = deps.env || process.env;
  const trustedNow = exactInstant((deps.now || (() => new Date().toISOString()))(), "Anicca EN widget canary clock");
  const clock = () => trustedNow;
  const config = laneConfig(env, parsed);
  const storeObject = deps.objectStore || createContentObjectStore({ objectDir: path.join(config.dataDir, "objects") });
  const pack = verifyInputs(config, storeObject);
  config.packCaption = pack.caption;
  config.visualEvidenceRef = pack.visualEvidenceRef;
  required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
  required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
  required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID");

  const secretBase = deps.secretProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId) throw new Error("Anicca EN widget secret tenant scope mismatch");
    if (ref === TOKEN_REF) return env.LM_POSTIZ_API_KEY;
    if (ref === TELEGRAM_TOKEN_REF) return env.LM_TELEGRAM_BOT_TOKEN;
    throw new Error("Anicca EN widget secret reference is not allowed");
  } };
  const secretProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ![TOKEN_REF, TELEGRAM_TOKEN_REF].includes(ref)) throw new Error("Anicca EN widget secret scope mismatch");
    const value = await secretBase.get(tenant, ref);
    if (typeof value !== "string" || !value.trim()) throw new Error("Anicca EN widget secret is invalid");
    return value;
  } };
  const integrationBase = deps.integrationProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== INTEGRATION_REF) throw new Error("Anicca EN widget integration scope mismatch");
    return INTEGRATION_ID;
  } };
  const integrationProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== INTEGRATION_REF) throw new Error("Anicca EN widget integration scope mismatch");
    const value = await integrationBase.get(tenant, ref);
    if (value !== INTEGRATION_ID) throw new Error("Anicca EN widget integration must return raw ID");
    return value;
  } };
  const chatBase = deps.chatProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== CHAT_REF) throw new Error("Anicca EN widget Telegram chat scope mismatch");
    return env.LM_TELEGRAM_ALERT_CHAT_ID;
  } };
  const chatProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== CHAT_REF) throw new Error("Anicca EN widget Telegram chat scope mismatch");
    const value = await chatBase.get(tenant, ref);
    if (typeof value !== "string" || !value.trim()) throw new Error("Anicca EN widget Telegram chat is invalid");
    return value;
  } };
  const store = deps.store || createMarketingLocalLedger({ dataDir: config.dataDir, env, now: clock });
  const publicationJob = buildMarketingVideoPublicationJob({ tenantId: config.tenantId, productId: PRODUCT, formatId: FORMAT, form: FORM, locale: LOCALE, slot: config.slot, creativeId: CREATIVE_ID, platform: PLATFORM, videoRef: config.videoRef, captionRef: config.captionRef, approvalRef: config.approvalRef, instagramProfileRef: PROFILE_REF, instagramIntegrationRef: INTEGRATION_REF, postizTokenRef: TOKEN_REF });
  const runDistribution = deps.runDistribution || runDistributionProcess;
  const publicationAdapter = createMarketingVideoPublicationLoopAdapter({
    objectStore: storeObject,
    secretProvider,
    integrationProvider,
    ledgerPath: () => publicationLedgerPath(config.dataDir, config.tenantId),
    runDistribution: async (input) => {
      let result;
      try { result = await runDistribution(input); } catch { const error = new Error("Anicca EN widget provider call failed"); error.unknownEffect = true; throw error; }
      const reconciled = result && (result.provider_reconciled === true || (result.provider_reconciled === undefined && result.reconciled === true));
      if (!result || typeof result !== "object" || result.platform !== PLATFORM || !directReel(result.public_url) || !reconciled) {
        const error = new Error("Anicca EN widget provider returned no reconciled direct Reel"); error.unknownEffect = true; throw error;
      }
      return result.provider_reconciled === true ? result : { ...result, provider_reconciled: true };
    },
    now: clock,
  });
  const existingPublication = await store.readReceipt({ tenantId: publicationJob.tenant_id, jobId: publicationJob.job_id });
  const controls = existingPublication ? null : armControls(config, publicationJob);
  let publicationQueued;
  let publicationRun;
  let publicationError;
  let restoreError;
  try {
    publicationQueued = await store.enqueueJob({ ...publicationJob, availableAt: trustedNow });
    publicationRun = await executeJob(store, publicationJob, (job) => publicationAdapter.execute(job), deps.executeCapabilityJob || executeCapabilityJob);
  } catch (error) {
    publicationError = error;
  } finally {
    if (controls) {
      try { restoreControls(controls.paths, controls); } catch (error) { restoreError = error; }
    }
  }
  if (restoreError) {
    const error = new Error("Anicca EN widget publication controls could not be restored");
    error.unknownEffect = true;
    if (publicationError) error.cause = publicationError;
    throw error;
  }
  if (publicationError) throw publicationError;
  const publication = publicationRun.receipt;
  if (!verifyMarketingVideoPublicationReceipt(publication) || publication.provider_reconciled !== true || publication.platform !== PLATFORM || !directReel(publication.public_url)) { const error = new Error("Anicca EN widget publication receipt is not reconciled"); error.unknownEffect = true; throw error; }
  const publicationResult = { created: publicationQueued.created && publicationRun.created, public_url: publication.public_url, provider_post_id: publication.provider_post_id };
  if (!(await verifyNativeObject(config.verificationRef, storeObject, config, publication, trustedNow, { fetchImpl: deps.fetchImpl, comparator: deps.videoComparator }))) return { slot: config.slot, publication: publicationResult, telegram: { created: false, held: true, message_id: null } };

  const telegramJob = buildMarketingLivenessJob({ tenantId: config.tenantId, telegramTokenRef: TELEGRAM_TOKEN_REF, telegramChatRef: CHAT_REF, payload: { lane: LANE, product: PRODUCT, locale: LOCALE, platform: PLATFORM, account: ACCOUNT_ID, slot: config.slot, status: "published", public_url: publication.public_url, retry_state: "not_required" } });
  const telegramQueued = await store.enqueueJob({ ...telegramJob, availableAt: trustedNow });
  const telegramRun = await executeJob(store, telegramJob, (job) => executeMarketingLivenessJob(job, { secretProvider, chatProvider, sendTelegram: deps.sendTelegram, now: clock }), deps.executeCapabilityJob || executeCapabilityJob);
  return { slot: config.slot, publication: publicationResult, telegram: { created: telegramQueued.created && telegramRun.created, held: false, message_id: telegramRun.receipt.message_id } };
}

if (require.main === module) runAniccaEnWidgetCanary(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { ACCOUNT_ID, INTEGRATION_ID, INTEGRATION_REF, LANE, PROFILE_REF, compareNativeVideo, parseArgs, runAniccaEnWidgetCanary, verifyNativeObject };
