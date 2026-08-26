#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const net = require("node:net");
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

const EN_LANE = Object.freeze({
  name: "EN",
  tenant: "dais-local",
  product: "anicca-ios",
  locale: "en",
  platform: "instagram",
  account: "@anicca.en",
  nativeAccount: "@anicca.en",
  manifestAccount: "anicca-ios-en-widget-instagram",
  profileRef: "profile://instagram/anicca.en",
  integrationRef: "integration://postiz/instagram/cmn8y95rg02d2qx0y09bbk5pb",
  integrationId: "cmn8y95rg02d2qx0y09bbk5pb",
  renderer: "reelclaw-widget",
  format: "reelclaw-widget",
  packFormat: "widget-demo-reel",
  form: "lockscreen-affirmation-widget",
  lane: "anicca-en-widget-instagram",
  creativeId: "EN-WIDGET-CANARY-98f4ce8c607a",
  tokenRef: "secret://postiz/api-key",
  telegramTokenRef: "secret://telegram/bot-token",
  chatRef: "telegram-chat://owner",
  packEnv: "LM_ANICCA_EN_WIDGET_PACK_REF",
  videoEnv: "LM_ANICCA_EN_WIDGET_VIDEO_REF",
  captionEnv: "LM_ANICCA_EN_WIDGET_CAPTION_REF",
  approvalEnv: "LM_ANICCA_EN_WIDGET_APPROVAL_REF",
  verificationEnv: "LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF",
  approvedPackName: "anicca-ios-reelclaw-widget-en.pack.json",
  workerLabel: "anicca-en-widget-canary",
  enforceApprovedPack: false,
});

const JA_LANE = Object.freeze({
  name: "JA",
  tenant: "dais-local",
  product: "anicca-ios",
  locale: "ja",
  platform: "instagram",
  account: "@anicca.jp.videos",
  nativeAccount: "@anicca.jp.videos",
  manifestAccount: "anicca-ios-ja-widget-instagram",
  profileRef: "profile://instagram/anicca.jp.videos",
  integrationRef: "integration://postiz/instagram/cmmzzg2es0539p30ycb94ayx0",
  integrationId: "cmmzzg2es0539p30ycb94ayx0",
  renderer: "reelclaw-widget",
  format: "reelclaw-widget",
  packFormat: "widget-demo-reel",
  form: "lockscreen-affirmation-widget",
  lane: "anicca-ja-widget-instagram",
  creativeId: "JA-WIDGET-CANARY-0c67b0a4d1de",
  tokenRef: "secret://postiz/api-key",
  telegramTokenRef: "secret://telegram/bot-token",
  chatRef: "telegram-chat://owner",
  packEnv: "LM_ANICCA_JA_WIDGET_PACK_REF",
  videoEnv: "LM_ANICCA_JA_WIDGET_VIDEO_REF",
  captionEnv: "LM_ANICCA_JA_WIDGET_CAPTION_REF",
  approvalEnv: "LM_ANICCA_JA_WIDGET_APPROVAL_REF",
  verificationEnv: "LM_ANICCA_JA_WIDGET_NATIVE_VERIFICATION_REF",
  approvedPackName: "anicca-ios-reelclaw-widget-ja.pack.json",
  workerLabel: "anicca-ja-widget-canary",
  enforceApprovedPack: true,
});

const JA_CARD_LANE = Object.freeze({
  name: "JACARD",
  tenant: "dais-local",
  product: "anicca-ios",
  locale: "ja",
  platform: "instagram",
  account: "@anicca.jp1",
  nativeAccount: "@anicca.ios.jp",
  manifestAccount: "anicca-ios-ja-instagram",
  profileRef: "profile://instagram/anicca.jp1",
  integrationRef: "integration://postiz/instagram/cmn8ycvtn02djqx0ytuisn9mw",
  integrationId: "cmn8ycvtn02djqx0ytuisn9mw",
  renderer: "reelclaw-card",
  format: "reelclaw-card",
  packFormat: "nudge-card-reel",
  form: "nudge-card",
  lane: "anicca-ja-card-instagram",
  creativeId: "JA-CARD-CANARY-35a15c7ce990",
  tokenRef: "secret://postiz/api-key",
  telegramTokenRef: "secret://telegram/bot-token",
  chatRef: "telegram-chat://owner",
  packRef: "object://sha256/76937db0d86478ea0a8dc8ca7fa9d38f3283b5cf491a6a334068f23b73fe311c",
  videoRef: "object://sha256/35a15c7ce990b1f05b1c8fa1b9665ff552db13f30e3c562b19f0724fac4e9a15",
  captionRef: "object://sha256/311f9c3dbf5ae7e904fa556d3ddf2555ba3445f198d721c442e6a620646ba2eb",
  approvalRef: "object://sha256/bb3e2ac385d7c7ed9a2387522ba441ece797fd8bcc9827c9386dcf66db764ee2",
  packEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_PACK_REF",
  videoEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_VIDEO_REF",
  captionEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_CAPTION_REF",
  approvalEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_APPROVAL_REF",
  verificationEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_NATIVE_VERIFICATION_REF",
  approvedPackName: "anicca-ios-reelclaw-card-ja.pack.json",
  workerLabel: "anicca-ja-card-instagram-canary",
  enforceApprovedPack: true,
});

const OBOU_LANE = Object.freeze({
  name: "OBOU",
  tenant: "dais-local",
  product: "anicca-ios",
  locale: "ja",
  platform: "instagram",
  account: "@obou.anicca",
  nativeAccount: "@obou.anicca",
  manifestAccount: "anicca-ios-ja-obou-instagram",
  profileRef: "profile://instagram/obou.anicca",
  integrationRef: "integration://postiz/instagram/cmooplxmu04tpmd0y4h3cpk33",
  integrationId: "cmooplxmu04tpmd0y4h3cpk33",
  renderer: "watercolor",
  format: "watercolor",
  packFormat: "watercolor-reel",
  form: "buddhist-self-care-reel",
  lane: "anicca-ja-obou-instagram",
  creativeId: "JA-WATERCOLOR-OBOU-b2772de4303a",
  tokenRef: "secret://postiz/api-key",
  telegramTokenRef: "secret://telegram/bot-token",
  chatRef: "telegram-chat://owner",
  packRef: "object://sha256/2a24da50040c9a2705c2e8975d76152b6add447504ac21493cdfca999f598145",
  videoRef: "object://sha256/b2772de4303acc901f42b43a0b3f4af166ae3daeb5ee7fd24e090e5b62f2b0e8",
  captionRef: "object://sha256/40293be368c6c33b04bb6fa6be8ff4bc879ca8c6d18c2944d7275c488088ac0a",
  approvalRef: "object://sha256/2fb66c87729a915545ca94d0029562240e543bad3f2bb9080ffc3fa821a538d7",
  packEnv: "LM_ANICCA_OBOU_INSTAGRAM_PACK_REF",
  videoEnv: "LM_ANICCA_OBOU_INSTAGRAM_VIDEO_REF",
  captionEnv: "LM_ANICCA_OBOU_INSTAGRAM_CAPTION_REF",
  approvalEnv: "LM_ANICCA_OBOU_INSTAGRAM_APPROVAL_REF",
  verificationEnv: "LM_ANICCA_OBOU_INSTAGRAM_NATIVE_VERIFICATION_REF",
  approvedPackName: "anicca-ios-watercolor-buddhist-ja.pack.json",
  workerLabel: "anicca-obou-instagram-canary",
  enforceApprovedPack: true,
});

function assertTrustedLane(lane) {
  if (lane !== EN_LANE && lane !== JA_LANE && lane !== JA_CARD_LANE && lane !== OBOU_LANE) throw new Error("Anicca widget lane identity is not trusted");
  return lane;
}

// Keep the original EN constants as aliases for existing callers/tests.
const TENANT = EN_LANE.tenant;
const PRODUCT = EN_LANE.product;
const LOCALE = EN_LANE.locale;
const PLATFORM = EN_LANE.platform;
const ACCOUNT_ID = EN_LANE.account;
const MANIFEST_ACCOUNT = EN_LANE.manifestAccount;
const PROFILE_REF = EN_LANE.profileRef;
const INTEGRATION_REF = EN_LANE.integrationRef;
const INTEGRATION_ID = EN_LANE.integrationId;
const RENDERER = EN_LANE.renderer;
const FORMAT = EN_LANE.format;
const PACK_FORMAT = EN_LANE.packFormat;
const FORM = EN_LANE.form;
const LANE = EN_LANE.lane;
const CREATIVE_ID = EN_LANE.creativeId;
const TOKEN_REF = EN_LANE.tokenRef;
const TELEGRAM_TOKEN_REF = EN_LANE.telegramTokenRef;
const CHAT_REF = EN_LANE.chatRef;
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

function decodeJsonUnicodeEscapes(value) {
  return String(value || "").replace(/\\+u([0-9a-f]{4})/gi, (_match, code) => String.fromCharCode(parseInt(code, 16)));
}

function embedVideoUrl(html) {
  if (!/GraphVideo/i.test(html)) return null;
  let decoded = String(html || "");
  for (let i = 0; i < 3; i += 1) decoded = decoded.replace(/\\"/g, '"').replace(/\\\//g, "/");
  const match = /["']video_url["']\s*:\s*["']([^"']+)["']/i.exec(decoded);
  if (!match) return null;
  try {
    const parsed = new URL(decodeJsonUnicodeEscapes(match[1]));
    if (parsed.protocol !== "https:" || parsed.port || parsed.username || parsed.password || parsed.hash
      || !/(^|\.)cdninstagram\.com$|(^|\.)fbcdn\.net$/i.test(parsed.hostname)) return null;
    return parsed.toString();
  } catch { return null; }
}

const MAX_LIVE_RESPONSE_BYTES = 50 * 1024 * 1024;
const DNS_ERROR_CODES = new Set(["ENOTFOUND", "EAI_AGAIN", "EAI_FAIL", "EAI_NONAME", "EAI_NODATA"]);

function ipv4Number(value) {
  if (!net.isIPv4(value)) return null;
  const parts = String(value).split(".");
  if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part) || Number(part) > 255)) return null;
  return (((Number(parts[0]) << 24) >>> 0) | (Number(parts[1]) << 16) | (Number(parts[2]) << 8) | Number(parts[3])) >>> 0;
}

function isPublicIPv4(value) {
  const address = ipv4Number(value);
  if (address == null) return false;
  const ranges = [
    [0x00000000, 8], // unspecified / "this" network
    [0x0a000000, 8], // private
    [0x64400000, 10], // shared address space
    [0x7f000000, 8], // loopback
    [0xa9fe0000, 16], // link-local
    [0xac100000, 12], // private
    [0xc0000000, 24], // IETF protocol assignments / reserved
    [0xc0000200, 24], // documentation
    [0xc0586300, 24], // deprecated 6to4 anycast
    [0xc0a80000, 16], // private
    [0xc6120000, 15], // benchmarking
    [0xc6336400, 24], // documentation
    [0xcb007100, 24], // documentation
    [0xe0000000, 4], // multicast
    [0xf0000000, 4], // reserved
  ];
  return !ranges.some(([base, bits]) => {
    const mask = bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
    return (address & mask) >>> 0 === base;
  });
}

function isAllowedFallbackHost(host) {
  return host === "www.instagram.com"
    || /(^|\.)cdninstagram\.com$/i.test(host)
    || /(^|\.)fbcdn\.net$/i.test(host);
}

function fallbackTarget(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || parsed.port || parsed.username || parsed.password || parsed.hash || !isAllowedFallbackHost(parsed.hostname)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function resolvePublicIPv4(host, options = {}) {
  if (!isAllowedFallbackHost(host)) throw new Error("Instagram fallback host is not allowed");
  const digRunner = options.digRunner || ((args) => spawnSync("dig", args, { encoding: "utf8", timeout: 5_000, maxBuffer: 64 * 1024 }));
  const result = digRunner(["@1.1.1.1", "+short", "A", host]);
  const output = String(result && result.stdout || "").trim();
  const rows = output ? output.split(/\s+/) : [];
  const addresses = rows.filter((row) => net.isIPv4(row));
  const aliases = rows.filter((row) => !net.isIPv4(row));
  if (!result || result.status !== 0 || addresses.length < 1
    || addresses.some((address) => !isPublicIPv4(address))
    || aliases.some((alias) => !/^(?:[A-Za-z0-9-]+\.)+[A-Za-z0-9-]+\.$/.test(alias))) {
    throw new Error("Instagram fallback DNS result is invalid");
  }
  return addresses[0];
}

function curlResponse(url, options = {}) {
  const parsed = fallbackTarget(url);
  if (!parsed) throw new Error("Instagram fallback URL is not allowed");
  const host = parsed.hostname;
  const address = resolvePublicIPv4(host, options);
  const args = [
    "--silent", "--show-error", "--fail-with-body", "--max-time", "20", "--connect-timeout", "5",
    "--max-filesize", String(MAX_LIVE_RESPONSE_BYTES), "--max-redirs", "0",
    "--proto", "=https", "--proto-redir", "=https",
    "--noproxy", "*",
    "--resolve", `${host}:443:${address}`, "--dump-header", "-", "--url", url,
  ];
  const curlRunner = options.curlRunner || ((commandArgs) => spawnSync("curl", commandArgs, { timeout: 25_000, maxBuffer: MAX_LIVE_RESPONSE_BYTES + 64 * 1024 }));
  const result = curlRunner(args);
  if (!result || result.status !== 0) throw new Error("Instagram fallback transport failed");
  const raw = Buffer.isBuffer(result && result.stdout) ? result.stdout : Buffer.from(String(result && result.stdout || ""));
  const separator = Buffer.from("\r\n\r\n");
  const offset = raw.indexOf(separator);
  const headers = offset >= 0 ? raw.subarray(0, offset).toString("latin1") : "";
  const body = offset >= 0 ? raw.subarray(offset + separator.length) : raw;
  if (body.length > MAX_LIVE_RESPONSE_BYTES) throw new Error("Instagram fallback response is too large");
  const statuses = [...headers.matchAll(/^HTTP\/\d(?:\.\d)?\s+(\d{3})/gm)].map((match) => Number(match[1]));
  const status = statuses.at(-1) || 0;
  return {
    status,
    url,
    text: async () => body.toString("utf8"),
    arrayBuffer: async () => body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength),
  };
}

function isDnsLookupError(error) {
  let current = error;
  for (let depth = 0; current && depth < 5; depth += 1, current = current.cause) {
    if (DNS_ERROR_CODES.has(String(current.code || "").toUpperCase())) return true;
    if (/getaddrinfo\s+(?:ENOTFOUND|EAI_[A-Z_]+)/i.test(String(current.message || ""))) return true;
  }
  return false;
}

async function defaultLiveFetch(url, init, options = {}) {
  const fetcher = options.defaultFetch || globalThis.fetch;
  if (typeof fetcher !== "function") return null;
  try {
    return await fetcher(url, init);
  } catch (error) {
    if (!isDnsLookupError(error)) throw error;
    return curlResponse(url, options);
  }
}

function probeVideo(file, ffprobeBin = "ffprobe", timeoutMs = 60_000) {
  const result = spawnSync(ffprobeBin, ["-v", "error", "-count_frames", "-print_format", "json", "-show_streams", "-show_format", file], {
    encoding: "utf8", maxBuffer: 2 * 1024 * 1024, timeout: timeoutMs,
  });
  if (!result || result.status !== 0) return null;
  try {
    const parsed = JSON.parse(result.stdout || "{}");
    const stream = (parsed.streams || []).find((item) => item.codec_type === "video");
    const duration = Number(stream && (stream.duration || parsed.format && parsed.format.duration));
    const width = Number(stream && stream.width);
    const height = Number(stream && stream.height);
    const frames = Number(stream && stream.nb_read_frames);
    if (!stream || !Number.isFinite(duration) || duration <= 0 || !Number.isSafeInteger(width) || width < 2 || !Number.isSafeInteger(height) || height < 2 || !Number.isSafeInteger(frames) || frames < 1) return null;
    return { duration, aspect: width / height, width, height, frames };
  } catch { return null; }
}

function compareNativeVideo(nativePath, approvedPath, options = {}) {
  const requestedTimeout = Number(options.timeoutMs);
  const timeoutMs = Number.isFinite(requestedTimeout) && requestedTimeout > 0
    ? Math.max(1, Math.min(60_000, Math.floor(requestedTimeout)))
    : 60_000;
  const native = probeVideo(nativePath, options.ffprobeBin || "ffprobe", timeoutMs);
  const approved = probeVideo(approvedPath, options.ffprobeBin || "ffprobe", timeoutMs);
  if (!native || !approved) return false;
  const durationDelta = Math.abs(native.duration - approved.duration);
  if (durationDelta > 0.25) return false;
  if (Math.abs(native.aspect - approved.aspect) > 0.03) return false;
  if (native.frames !== approved.frames) return false;
  const width = approved.width;
  const height = approved.height;
  const expectedFrames = native.frames;
  const pad = (label) => `[${label}:v]setpts=PTS-STARTPTS,scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p`;
  const compare = (filter) => {
    const result = spawnSync(options.ffmpegBin || "ffmpeg", ["-loglevel", "error", "-i", nativePath, "-i", approvedPath, "-filter_complex", filter, "-frames:v", String(expectedFrames), "-f", "null", "-"], {
      encoding: "utf8", maxBuffer: 2 * 1024 * 1024, timeout: timeoutMs,
    });
    const output = `${result && result.stdout || ""}\n${result && result.stderr || ""}`;
    const scores = [...output.matchAll(/All:(-?[0-9.]+)/g)].map((match) => Number(match[1]));
    const comparedFrames = (output.match(/\bn:\d+/g) || []).length;
    const full = Boolean(result && result.status === 0 && comparedFrames === expectedFrames && scores.length === expectedFrames);
    return {
      ok: full && scores.every((score) => score >= 0.945),
      full,
      comparedFrames,
      scores,
    };
  };
  const strict = compare(`${pad("0")} [native];${pad("1")} [approved];[native][approved]ssim=stats_file=-`);
  if (strict.ok) return true;
  if (!strict.full) return false;
  const rawMean = strict.scores.reduce((sum, score) => sum + score, 0) / strict.scores.length;
  if (Math.min(...strict.scores) < 0.90 || rawMean < 0.945) return false;
  const blurPad = (label) => `[${label}:v]setpts=PTS-STARTPTS,scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=black,gblur=sigma=2,format=yuv420p`;
  const blurred = compare(`${blurPad("0")} [native];${blurPad("1")} [approved];[native][approved]ssim=stats_file=-`);
  return Boolean(blurred.full && blurred.comparedFrames === expectedFrames && blurred.ok);
}

function parseArgs(argv = [], lane = EN_LANE) {
  lane = assertTrustedLane(lane);
  if (argv.length === 3 && argv[0] === "run" && argv[1] === "--slot") {
    return { command: "run", slot: exactInstant(argv[2], `Anicca ${lane.name} widget canary slot`) };
  }
  throw new Error(`usage: anicca-${lane.name.toLowerCase()}-widget-canary.js run --slot <exact ISO instant>`);
}

function laneConfig(env, parsed, lane = EN_LANE) {
  const rawDataDir = required(env.LM_DATA_DIR, "LM_DATA_DIR");
  const dataDir = path.resolve(rawDataDir);
  if (!path.isAbsolute(rawDataDir) || dataDir === path.parse(dataDir).root) throw new Error("LM_DATA_DIR is invalid");
  const tenantId = required(env.LM_RUNTIME_TENANT_ID, "LM_RUNTIME_TENANT_ID");
  if (tenantId !== lane.tenant) throw new Error(`Anicca ${lane.name} widget canary tenant is invalid`);
  const config = {
    dataDir,
    tenantId,
    slot: parsed.slot,
    packRef: objectRef(env[lane.packEnv], `Anicca ${lane.name} widget pack`),
    videoRef: objectRef(env[lane.videoEnv], `Anicca ${lane.name} widget video`),
    captionRef: objectRef(env[lane.captionEnv], `Anicca ${lane.name} widget caption`),
    approvalRef: objectRef(env[lane.approvalEnv], `Anicca ${lane.name} widget approval`),
    verificationRef: String(env[lane.verificationEnv] || "").trim() || null,
    lane,
  };
  for (const [label, actual, expected] of [
    ["pack", config.packRef, lane.packRef],
    ["video", config.videoRef, lane.videoRef],
    ["caption", config.captionRef, lane.captionRef],
    ["approval", config.approvalRef, lane.approvalRef],
  ]) {
    if (expected !== undefined && actual !== expected) throw new Error(`Anicca ${lane.name} widget ${label} reference mismatch`);
  }
  if (config.verificationRef) objectRef(config.verificationRef, `Anicca ${lane.name} widget native verification`);
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

function verifyInputs(config, store, lane = config.lane || EN_LANE) {
  const packObject = readJson(store, config.packRef, `Anicca ${lane.name} widget pack`);
  const approvalObject = readJson(store, config.approvalRef, `Anicca ${lane.name} widget approval`);
  store.resolve(config.videoRef);
  const captionPath = store.resolve(config.captionRef);
  const pack = packObject.value;
  const approval = approvalObject.value;
  const media = pack && Array.isArray(pack.media) && pack.media.length === 1 ? pack.media[0] : null;
  if (
    !pack || typeof pack !== "object" || Array.isArray(pack)
    || pack.schema_version !== 1 || pack.kind !== "marketing_video_asset_pack"
    || pack.product_id !== lane.product || pack.locale !== lane.locale || pack.platform !== lane.platform
    || pack.account_id !== lane.account || pack.integration_id !== lane.integrationId
    || pack.renderer_id !== lane.renderer || pack.format_id !== lane.packFormat || pack.form !== lane.form
    || pack.caption_ref !== config.captionRef || typeof pack.caption !== "string"
    || !media || typeof media !== "object" || media.video_ref !== config.videoRef
  ) throw new Error(`Anicca ${lane.name} widget pack identity mismatch`);
  if (!Buffer.from(pack.caption, "utf8").equals(fs.readFileSync(captionPath))) throw new Error(`Anicca ${lane.name} widget pack caption mismatch`);
  const visualEvidenceRef = objectRef(pack.visual_evidence_ref, `Anicca ${lane.name} widget visual evidence`);
  store.resolve(visualEvidenceRef);
  const approvalAccount = Object.hasOwn(approval || {}, "account_id") ? approval.account_id : approval && approval.account;
  if (
    !approval || typeof approval !== "object" || Array.isArray(approval)
    || approval.schema_version !== 1 || approval.kind !== "marketing_video_publication_approval"
    || approval.status !== "approved" || approval.tenant_id !== lane.tenant || approval.product_id !== lane.product
    || approval.format_id !== lane.format || approval.form !== lane.form || approval.locale !== lane.locale
    || approval.platform !== lane.platform || approvalAccount !== lane.account
    || approval.integration_ref !== lane.integrationRef || approval.pack_ref !== config.packRef
    || approval.creative_id !== lane.creativeId || approval.video_sha256 !== hashRef(config.videoRef)
    || approval.caption_sha256 !== hashRef(config.captionRef)
  ) throw new Error(`Anicca ${lane.name} widget approval mismatch`);
  return { caption: pack.caption, visualEvidenceRef };
}

async function executeJob(store, job, handler, execute = executeCapabilityJob, lane = EN_LANE) {
  let receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (receipt) return { created: false, receipt };
  const claim = await store.claimJob({ tenantId: job.tenant_id, jobId: job.job_id, capability: job.capability, workerId: lane.workerLabel, leaseSeconds: 300 });
  if (!claim) {
    receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
    if (receipt) return { created: false, receipt };
    const state = await store.readJob({ tenantId: job.tenant_id, jobId: job.job_id });
    const error = new Error(`Anicca ${lane.name} widget ${job.capability} job is not claimable`);
    if (state && state.unknown_effect === true) error.unknownEffect = true;
    throw error;
  }
  await execute(claim, {
    workerId: lane.workerLabel,
    handlers: { [job.capability]: handler },
    heartbeatJob: (input) => store.heartbeatJob(input),
    completeJob: (input) => store.completeJob(input),
    failJob: (input) => store.failJob(input),
    leaseSeconds: 300,
  });
  receipt = await store.readReceipt({ tenantId: job.tenant_id, jobId: job.job_id });
  if (!receipt) {
    const state = await store.readJob({ tenantId: job.tenant_id, jobId: job.job_id });
    const error = new Error(`Anicca ${lane.name} widget ${job.capability} receipt is unavailable`);
    if (state && state.unknown_effect === true) error.unknownEffect = true;
    throw error;
  }
  return { created: true, receipt };
}

async function verifyNativeObject(ref, store, config, receipt, trustedNow, options = {}, lane = config.lane || EN_LANE) {
  if (!ref) return false;
  try {
    const verificationObject = readJson(store, ref, `Anicca ${lane.name} widget native verification`).value;
    const account = Object.hasOwn(verificationObject || {}, "account_id") ? verificationObject.account_id : verificationObject && verificationObject.account;
    const evidenceRef = objectRef(verificationObject && verificationObject.evidence_ref, `Anicca ${lane.name} widget native evidence`);
    const evidence = readJson(store, evidenceRef, `Anicca ${lane.name} widget native evidence`).value;
    const nativeVideoRef = objectRef(evidence && evidence.native_video_ref, `Anicca ${lane.name} widget native video`);
    const nativeContactSheetRef = objectRef(evidence && evidence.native_contact_sheet_ref, `Anicca ${lane.name} widget native contact sheet`);
    store.resolve(nativeVideoRef);
    store.resolve(nativeContactSheetRef);
    const verifiedAt = exactInstant(verificationObject.verified_at, `Anicca ${lane.name} widget native verification verified_at`);
    const publishedAt = exactInstant(receipt.published_at, `Anicca ${lane.name} widget publication published_at`);
    const observedAt = exactInstant(evidence.observed_at, `Anicca ${lane.name} widget native evidence observed_at`);
    if (!(verificationObject && typeof verificationObject === "object" && !Array.isArray(verificationObject)
      && verificationObject.schema_version === 1 && verificationObject.kind === "marketing_video_native_verification"
      && verificationObject.status === "verified" && verificationObject.product_id === lane.product && account === lane.account
      && verificationObject.integration_ref === lane.integrationRef && verificationObject.public_url === receipt.public_url
      && verificationObject.pack_sha256 === hashRef(config.packRef) && verificationObject.video_sha256 === hashRef(config.videoRef)
      && verificationObject.caption_sha256 === hashRef(config.captionRef)
      && evidence && typeof evidence === "object" && !Array.isArray(evidence)
      && evidence.schema_version === 1 && evidence.kind === "marketing_video_native_evidence"
      && evidence.status === "verified" && evidence.platform === lane.platform
      && evidence.public_url === receipt.public_url && evidence.account_id === (lane.nativeAccount || lane.account)
      && evidence.integration_ref === lane.integrationRef && evidence.caption === config.packCaption
      && evidence.caption_sha256 === hashRef(config.captionRef) && evidence.video_sha256 === hashRef(config.videoRef)
      && evidence.observation_method === "instagram-captioned-embed+native-video-frame-comparison"
      && evidence.source_contact_sheet_ref === config.visualEvidenceRef
      && !["account_match", "caption_match", "content_match"].some((key) => Object.hasOwn(evidence, key)))) return false;
    if (options.fetchImpl !== undefined && options.fetchImpl !== null && typeof options.fetchImpl !== "function") return false;
    const fetchImpl = options.fetchImpl || ((url, init) => defaultLiveFetch(url, init, options));
    const embedUrl = `${receipt.public_url}embed/captioned/`;
    const embedResponse = await fetchImpl(embedUrl, { method: "GET", redirect: "follow" });
    if (!embedResponse || Number(embedResponse.status) !== 200 || typeof embedResponse.text !== "function") return false;
    if (embedResponse.url && embedResponse.url !== embedUrl) return false;
    const html = await embedResponse.text();
    const ownerPath = (lane.nativeAccount || lane.account).slice(1);
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
      && Date.parse(verifiedAt) <= Date.parse(exactInstant(trustedNow, `Anicca ${lane.name} widget trusted clock`));
  } catch {
    return false;
  }
}

function publicationLedgerPath(dataDir, tenantId, product = EN_LANE.product) {
  return path.join(dataDir, "tenants", encodeURIComponent(tenantId), "marketing", "video-publication", product, "distribution.jsonl");
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

function armControls(config, job, lane = config.lane || EN_LANE) {
  const paths = controlPaths(config.dataDir);
  const manifest = readControl(paths.manifest, `Anicca ${lane.name} widget lane manifest`);
  const fence = readControl(paths.fence, `Anicca ${lane.name} widget publication fence`);
  if (
    !isMarketingLaneManifest(manifest.value) || manifest.value.tenant_id !== lane.tenant
    || fence.value.schema_version !== 1 || fence.value.state !== "closed"
  ) throw new Error(`Anicca ${lane.name} widget publication controls are not closed`);
  const targets = manifest.value.lanes.filter((manifestLane) => (
    manifestLane.tenant_id === config.tenantId && manifestLane.product_id === "anicca" && manifestLane.locale === lane.locale
    && manifestLane.platform === lane.platform && manifestLane.account === lane.manifestAccount
    && manifestLane.profile === lane.account && manifestLane.integration_id === lane.integrationId
  ));
  if (targets.length !== 1 || manifest.value.lanes.some((manifestLane) => manifestLane.production_armed !== false)) throw new Error(`Anicca ${lane.name} widget target lane is not default-off`);
  const target = targets[0];
  if (
    target.provider !== "postiz" || target.disabled !== false || target.lane_state !== "default-off"
    || target.account !== lane.manifestAccount || target.profile !== lane.account
    || target.disposition !== "target" || target.production_armed !== false || target.owner !== "life-manager"
    || target.renderer !== lane.renderer || target.format !== lane.packFormat || target.canary_state !== "pack-ready"
    || (lane.enforceApprovedPack && target.approved_pack !== lane.approvedPackName)
    || !Number.isSafeInteger(target.target_daily_limit) || target.target_daily_limit < 1
  ) throw new Error(`Anicca ${lane.name} widget target lane identity is invalid`);
  const rows = manifest.value.lanes.map((manifestLane) => ({
    ...manifestLane,
    verified: true,
    ...(manifestLane.integration_id === lane.integrationId ? { lane_state: "production-armed", production_armed: true } : { production_armed: false }),
  }));
  const armed = createMarketingLaneManifest({
    tenant_id: lane.tenant,
    integrations: rows,
    holds: manifest.value.holds.map((hold) => ({ ...hold, verified: true })),
  }, { tenantId: lane.tenant, assignments: rows.map((row) => ({ ...row })) });
  const saved = { paths, manifest, fence };
  try {
    writeMarketingLaneManifest(armed, { dataDir: config.dataDir });
    atomicBytes(paths.fence, Buffer.from(`${JSON.stringify({ schema_version: 1, state: "open", allowed_effect_key: job.effect_key, reason: `one Anicca ${lane.name} widget canary` })}\n`), fence.mode);
  } catch (error) {
    try { restoreControls(paths, saved); } catch (restoreError) { error.unknownEffect = true; error.cause = restoreError; }
    throw error;
  }
  return saved;
}

async function runAniccaWidgetCanary(argv = [], deps = {}, lane = EN_LANE) {
  lane = assertTrustedLane(lane);
  const parsed = parseArgs(argv, lane);
  const env = deps.env || process.env;
  const trustedNow = exactInstant((deps.now || (() => new Date().toISOString()))(), `Anicca ${lane.name} widget canary clock`);
  const clock = () => trustedNow;
  const config = laneConfig(env, parsed, lane);
  const storeObject = deps.objectStore || createContentObjectStore({ objectDir: path.join(config.dataDir, "objects") });
  const pack = verifyInputs(config, storeObject, lane);
  config.packCaption = pack.caption;
  config.visualEvidenceRef = pack.visualEvidenceRef;
  required(env.LM_POSTIZ_API_KEY, "LM_POSTIZ_API_KEY");
  required(env.LM_TELEGRAM_BOT_TOKEN, "LM_TELEGRAM_BOT_TOKEN");
  required(env.LM_TELEGRAM_ALERT_CHAT_ID, "LM_TELEGRAM_ALERT_CHAT_ID");

  const secretBase = deps.secretProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId) throw new Error(`Anicca ${lane.name} widget secret tenant scope mismatch`);
    if (ref === lane.tokenRef) return env.LM_POSTIZ_API_KEY;
    if (ref === lane.telegramTokenRef) return env.LM_TELEGRAM_BOT_TOKEN;
    throw new Error(`Anicca ${lane.name} widget secret reference is not allowed`);
  } };
  const secretProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ![lane.tokenRef, lane.telegramTokenRef].includes(ref)) throw new Error(`Anicca ${lane.name} widget secret scope mismatch`);
    const value = await secretBase.get(tenant, ref);
    if (typeof value !== "string" || !value.trim()) throw new Error(`Anicca ${lane.name} widget secret is invalid`);
    return value;
  } };
  const integrationBase = deps.integrationProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== lane.integrationRef) throw new Error(`Anicca ${lane.name} widget integration scope mismatch`);
    return lane.integrationId;
  } };
  const integrationProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== lane.integrationRef) throw new Error(`Anicca ${lane.name} widget integration scope mismatch`);
    const value = await integrationBase.get(tenant, ref);
    if (value !== lane.integrationId) throw new Error(`Anicca ${lane.name} widget integration must return raw ID`);
    return value;
  } };
  const chatBase = deps.chatProvider || { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== lane.chatRef) throw new Error(`Anicca ${lane.name} widget Telegram chat scope mismatch`);
    return env.LM_TELEGRAM_ALERT_CHAT_ID;
  } };
  const chatProvider = { get: async (tenant, ref) => {
    if (tenant !== config.tenantId || ref !== lane.chatRef) throw new Error(`Anicca ${lane.name} widget Telegram chat scope mismatch`);
    const value = await chatBase.get(tenant, ref);
    if (typeof value !== "string" || !value.trim()) throw new Error(`Anicca ${lane.name} widget Telegram chat is invalid`);
    return value;
  } };
  const store = deps.store || createMarketingLocalLedger({ dataDir: config.dataDir, env, now: clock });
  const publicationJob = buildMarketingVideoPublicationJob({ tenantId: config.tenantId, productId: lane.product, formatId: lane.format, form: lane.form, locale: lane.locale, slot: config.slot, creativeId: lane.creativeId, platform: lane.platform, videoRef: config.videoRef, captionRef: config.captionRef, approvalRef: config.approvalRef, instagramProfileRef: lane.profileRef, instagramIntegrationRef: lane.integrationRef, postizTokenRef: lane.tokenRef });
  const runDistribution = deps.runDistribution || runDistributionProcess;
  const publicationAdapter = createMarketingVideoPublicationLoopAdapter({
    objectStore: storeObject,
    secretProvider,
    integrationProvider,
    ledgerPath: (_, product) => publicationLedgerPath(config.dataDir, config.tenantId, product || lane.product),
    runDistribution: async (input) => {
      let result;
      try { result = await runDistribution(input); } catch { const error = new Error(`Anicca ${lane.name} widget provider call failed`); error.unknownEffect = true; throw error; }
      const reconciled = result && (result.provider_reconciled === true || (result.provider_reconciled === undefined && result.reconciled === true));
      if (!result || typeof result !== "object" || result.platform !== lane.platform || !directReel(result.public_url) || !reconciled) {
        const error = new Error(`Anicca ${lane.name} widget provider returned no reconciled direct Reel`); error.unknownEffect = true; throw error;
      }
      return result.provider_reconciled === true ? result : { ...result, provider_reconciled: true };
    },
    now: clock,
  });
  const existingPublication = await store.readReceipt({ tenantId: publicationJob.tenant_id, jobId: publicationJob.job_id });
  const controls = existingPublication ? null : armControls(config, publicationJob, lane);
  let publicationQueued;
  let publicationRun;
  let publicationError;
  let restoreError;
  try {
    publicationQueued = await store.enqueueJob({ ...publicationJob, availableAt: trustedNow });
    publicationRun = await executeJob(store, publicationJob, (job) => publicationAdapter.execute(job), deps.executeCapabilityJob || executeCapabilityJob, lane);
  } catch (error) {
    publicationError = error;
  } finally {
    if (controls) {
      try { restoreControls(controls.paths, controls); } catch (error) { restoreError = error; }
    }
  }
  if (restoreError) {
    const error = new Error(`Anicca ${lane.name} widget publication controls could not be restored`);
    error.unknownEffect = true;
    if (publicationError) error.cause = publicationError;
    throw error;
  }
  if (publicationError) throw publicationError;
  const publication = publicationRun.receipt;
  if (!verifyMarketingVideoPublicationReceipt(publication) || publication.provider_reconciled !== true || publication.platform !== lane.platform || !directReel(publication.public_url)) { const error = new Error(`Anicca ${lane.name} widget publication receipt is not reconciled`); error.unknownEffect = true; throw error; }
  const publicationResult = { created: publicationQueued.created && publicationRun.created, public_url: publication.public_url, provider_post_id: publication.provider_post_id };
  if (!(await verifyNativeObject(config.verificationRef, storeObject, config, publication, trustedNow, {
    fetchImpl: deps.fetchImpl,
    defaultFetch: deps.defaultFetch,
    digRunner: deps.digRunner,
    curlRunner: deps.curlRunner,
    comparator: deps.videoComparator,
  }, lane))) return { slot: config.slot, publication: publicationResult, telegram: { created: false, held: true, message_id: null } };

  const telegramJob = buildMarketingLivenessJob({ tenantId: config.tenantId, telegramTokenRef: lane.telegramTokenRef, telegramChatRef: lane.chatRef, payload: { lane: lane.lane, product: lane.product, locale: lane.locale, platform: lane.platform, account: lane.nativeAccount || lane.account, slot: config.slot, status: "published", public_url: publication.public_url, retry_state: "not_required" } });
  const telegramQueued = await store.enqueueJob({ ...telegramJob, availableAt: trustedNow });
  const telegramRun = await executeJob(store, telegramJob, (job) => executeMarketingLivenessJob(job, { secretProvider, chatProvider, sendTelegram: deps.sendTelegram, now: clock }), deps.executeCapabilityJob || executeCapabilityJob, lane);
  return { slot: config.slot, publication: publicationResult, telegram: { created: telegramQueued.created && telegramRun.created, held: false, message_id: telegramRun.receipt.message_id } };
}

async function runAniccaEnWidgetCanary(argv = [], deps = {}) {
  return runAniccaWidgetCanary(argv, deps, EN_LANE);
}

if (require.main === module) runAniccaEnWidgetCanary(process.argv.slice(2)).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = {
  ACCOUNT_ID,
  EN_LANE,
  INTEGRATION_ID,
  INTEGRATION_REF,
  JA_LANE,
  JA_CARD_LANE,
  OBOU_LANE,
  LANE,
  PROFILE_REF,
  armControls,
  compareNativeVideo,
  curlResponse,
  decodeJsonUnicodeEscapes,
  defaultLiveFetch,
  embedVideoUrl,
  isDnsLookupError,
  isPublicIPv4,
  parseArgs,
  resolvePublicIPv4,
  runAniccaEnWidgetCanary,
  runAniccaWidgetCanary,
  restoreControls,
  verifyNativeObject,
};
