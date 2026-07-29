#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const { buildRuntimeJob } = require("./runtime-job-store.js");
const {
  createContentObjectStore,
  parseObjectRef,
} = require("./content-object-store.js");
const { resolveRuntimePaths } = require("./runtime-paths.js");

const CAPABILITY = "marketing.life-manager.daily.publish";
const LOOP_ID = "marketing.life-manager.daily";
const CREATIVE_REF = /^creative:\/\/life-manager\/([A-Za-z0-9._-]+)$/;
const PLATFORM_REF = /^platform:\/\/(instagram|tiktok)$/;
const PROFILE_REF = /^profile:\/\/instagram\/[a-z0-9._-]+$/i;
const SECRET_REF = /^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i;
const INTEGRATION_REF = /^integration:\/\/postiz\/tiktok\/[a-z0-9._-]+$/i;
const HASH = /^[0-9a-f]{64}$/;
const EFFECT_KEY = /^marketing:life-manager:(instagram|tiktok):([A-Za-z0-9._-]+):([0-9a-f]{64}):([0-9a-f]{64})$/;
const INSTAGRAM_URL = /^https:\/\/www\.instagram\.com\/(?:reel|p)\/[A-Za-z0-9_-]+\/?$/;
const TIKTOK_URL = /^https:\/\/www\.tiktok\.com\/@[^/]+\/video\/[0-9]+\/?$/;
const PROVIDER_POST_ID = /^[A-Za-z0-9._:-]{1,200}$/;
const PROVIDER_ROUTES = new Set([
  "instagram_file_script",
  "postiz",
  "direct_browser",
]);

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function matchRef(value, pattern, label) {
  const text = required(value, label);
  const match = pattern.exec(text);
  if (!match) throw new Error(`${label} reference is invalid`);
  return { text, match };
}

function parseCreativeRef(ref) {
  return matchRef(ref, CREATIVE_REF, "creative").match[1];
}

function effectContract(effectKey) {
  const match = EFFECT_KEY.exec(required(effectKey, "marketing effect key"));
  if (!match) throw new Error("marketing effect key is invalid");
  return {
    platform: match[1],
    creativeId: match[2],
    videoSha256: match[3],
    captionSha256: match[4],
  };
}

function buildMarketingDailyJob(input = {}) {
  const tenantId = required(input.tenantId, "marketing tenant");
  const creativeId = required(input.creativeId, "marketing creative");
  if (!/^[A-Za-z0-9._-]+$/.test(creativeId)) {
    throw new Error("marketing creative is invalid");
  }
  const platform = matchRef(
    `platform://${required(input.platform, "marketing platform")}`,
    PLATFORM_REF,
    "platform",
  ).match[1];
  const videoRef = matchRef(
    input.videoRef,
    /^object:\/\/sha256\/[0-9a-f]{64}$/,
    "video",
  ).text;
  const captionRef = matchRef(
    input.captionRef,
    /^object:\/\/sha256\/[0-9a-f]{64}$/,
    "caption",
  ).text;
  const approvalRef = matchRef(
    input.approvalRef,
    /^object:\/\/sha256\/[0-9a-f]{64}$/,
    "approval",
  ).text;
  const instagramProfileRef = matchRef(
    input.instagramProfileRef,
    PROFILE_REF,
    "Instagram profile",
  ).text;
  const postizTokenRef = matchRef(input.postizTokenRef, SECRET_REF, "Postiz token").text;
  const tiktokIntegrationRef = matchRef(
    input.tiktokIntegrationRef,
    INTEGRATION_REF,
    "TikTok integration",
  ).text;
  const videoHash = parseObjectRef(videoRef);
  const captionHash = parseObjectRef(captionRef);
  const digest = createHash("sha256")
    .update(`${tenantId}\n${platform}\n${creativeId}\n${videoHash}\n${captionHash}`, "utf8")
    .digest("hex");
  return buildRuntimeJob({
    jobId: `marketing-daily:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "publish",
    effectKey: `marketing:life-manager:${platform}:${creativeId}:${videoHash}:${captionHash}`,
    inputRefs: {
      creative_ref: `creative://life-manager/${creativeId}`,
      platform_ref: `platform://${platform}`,
      video_ref: videoRef,
      caption_ref: captionRef,
      approval_ref: approvalRef,
      instagram_profile_ref: instagramProfileRef,
      postiz_token_ref: postizTokenRef,
      tiktok_integration_ref: tiktokIntegrationRef,
    },
    maxAttempts: 3,
  });
}

function tenantSegment(tenantId) {
  return encodeURIComponent(required(tenantId, "marketing tenant"));
}

function defaultLedgerPath(tenantId, paths) {
  return path.join(
    paths.dataDir,
    "tenants",
    tenantSegment(tenantId),
    "marketing",
    "life-manager-daily",
    "distribution.jsonl",
  );
}

function runDistributionProcess(input) {
  const repoRoot = path.resolve(__dirname, "../../..");
  const script = path.join(repoRoot, "skills/video/lm-distribution/distribute.py");
  const result = spawnSync(input.python || "python3", [
    script,
    "--creative-id", input.creativeId,
    "--platform", input.platform,
    "--video", input.videoPath,
    "--caption-file", input.captionPath,
    "--ledger", input.ledgerPath,
    "--approvals", input.approvalPath,
    "--instagram-handle", input.instagramHandle,
    "--instagram-accounts", input.instagramAccountsPath,
    "--instagram-settings", input.instagramSettingsPath,
    "--instagram-credentials", input.instagramCredentialsPath,
    "--instagram-profile-state", input.instagramProfileStatePath,
    "--tiktok-integration", input.tiktokIntegration,
  ], {
    cwd: repoRoot,
    env: {
      ...process.env,
      POSTIZ_API_KEY: input.postizToken,
    },
    encoding: "utf8",
    timeout: 20 * 60 * 1000,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (result.status !== 0) {
    const error = new Error(`marketing distribution failed with exit ${result.status}`);
    error.unknownEffect = true;
    throw error;
  }
  const lines = String(result.stdout || "").split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) {
    const error = new Error("marketing distribution returned invalid JSON");
    error.unknownEffect = true;
    throw error;
  }
  try {
    return JSON.parse(lines[0]);
  } catch {
    const error = new Error("marketing distribution returned invalid JSON");
    error.unknownEffect = true;
    throw error;
  }
}

function validDistributionResult(result, contract) {
  const urlPattern = contract.platform === "instagram" ? INSTAGRAM_URL : TIKTOK_URL;
  return result
    && typeof result === "object"
    && result.creative_id === contract.creativeId
    && result.video_sha256 === contract.videoSha256
    && result.caption_sha256 === contract.captionSha256
    && result.platform === contract.platform
    && urlPattern.test(String(result.public_url || ""));
}

function validProviderJoinKeys(result) {
  return Boolean(
    result
    && PROVIDER_POST_ID.test(String(result.provider_post_id || ""))
    && PROVIDER_ROUTES.has(result.provider_route),
  );
}

function validIso(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function verifyMarketingDailyReceipt(receipt) {
  return Boolean(
    receipt
    && typeof receipt === "object"
    && !Array.isArray(receipt)
    && receipt.schema_version === 1
    && receipt.kind === "marketing_daily_distribution"
    && receipt.status === "published"
    && ["instagram", "tiktok"].includes(receipt.platform)
    && (
      receipt.provider_reconciled === undefined
      || typeof receipt.provider_reconciled === "boolean"
    )
    && (
      (
        receipt.provider_post_id === undefined
        && receipt.provider_route === undefined
      )
      || (
        PROVIDER_POST_ID.test(String(receipt.provider_post_id || ""))
        && PROVIDER_ROUTES.has(receipt.provider_route)
      )
    )
    && /^[A-Za-z0-9._-]+$/.test(String(receipt.creative_id || ""))
    && HASH.test(String(receipt.video_sha256 || ""))
    && HASH.test(String(receipt.caption_sha256 || ""))
    && (
      receipt.platform === "instagram"
        ? INSTAGRAM_URL.test(String(receipt.public_url || ""))
        : TIKTOK_URL.test(String(receipt.public_url || ""))
    )
    && validIso(receipt.published_at),
  );
}

function safeMarketingDailySummary(receipt) {
  if (!verifyMarketingDailyReceipt(receipt)) {
    throw new Error("marketing daily receipt verification failed");
  }
  return {
    status: receipt.status,
    creative_id: receipt.creative_id,
    platform: receipt.platform,
    public_url: receipt.public_url,
    provider_post_id: receipt.provider_post_id || null,
    provider_route: receipt.provider_route || null,
    provider_reconciled: receipt.provider_reconciled === true,
    video_sha256: receipt.video_sha256,
    caption_sha256: receipt.caption_sha256,
  };
}

function defaultServices(deps) {
  let paths;
  const runtimePaths = () => {
    if (!paths) paths = resolveRuntimePaths(process.env);
    return paths;
  };
  return {
    objectStore: deps.objectStore || {
      resolve(ref) {
        return createContentObjectStore({
          objectDir: runtimePaths().objectDir,
        }).resolve(ref);
      },
    },
    profileProvider: deps.profileProvider,
    secretProvider: deps.secretProvider,
    integrationProvider: deps.integrationProvider,
    ledgerPath: deps.ledgerPath || ((tenantId) => defaultLedgerPath(tenantId, runtimePaths())),
    runDistribution: deps.runDistribution || runDistributionProcess,
    now: deps.now || (() => new Date().toISOString()),
  };
}

async function executeMarketingDailyJob(job, deps = {}) {
  if (
    !job
    || job.capability !== CAPABILITY
    || job.loop_id !== LOOP_ID
    || job.effect_class !== "publish"
  ) {
    throw new Error("marketing daily job contract mismatch");
  }
  const refs = job.input_refs || {};
  const creativeId = parseCreativeRef(refs.creative_ref);
  const platform = matchRef(refs.platform_ref, PLATFORM_REF, "platform").match[1];
  const contract = effectContract(job.effect_key);
  if (
    platform !== contract.platform
    ||
    creativeId !== contract.creativeId
    || parseObjectRef(refs.video_ref) !== contract.videoSha256
    || parseObjectRef(refs.caption_ref) !== contract.captionSha256
  ) {
    throw new Error("marketing daily tenant/content scope mismatch");
  }
  const services = defaultServices(deps);
  for (const [name, provider] of [
    ["profile", services.profileProvider],
    ["secret", services.secretProvider],
    ["integration", services.integrationProvider],
  ]) {
    if (!provider || typeof provider.get !== "function") {
      throw new Error(`marketing daily ${name} provider is required`);
    }
  }
  const videoPath = services.objectStore.resolve(refs.video_ref);
  const captionPath = services.objectStore.resolve(refs.caption_ref);
  const approvalPath = services.objectStore.resolve(refs.approval_ref);
  const profile = await services.profileProvider.get(
    job.tenant_id,
    refs.instagram_profile_ref,
  );
  if (
    !profile
    || !profile.handle
    || !profile.accountsPath
    || !profile.settingsPath
    || !profile.credentialsPath
    || !profile.stateDir
  ) {
    throw new Error("marketing daily Instagram profile is incomplete");
  }
  const postizToken = await services.secretProvider.get(
    job.tenant_id,
    refs.postiz_token_ref,
  );
  const tiktokIntegration = await services.integrationProvider.get(
    job.tenant_id,
    refs.tiktok_integration_ref,
  );
  const ledgerPath = services.ledgerPath(job.tenant_id);
  fs.mkdirSync(path.dirname(ledgerPath), { recursive: true, mode: 0o700 });
  let result;
  try {
    result = await services.runDistribution({
      creativeId,
      platform,
      videoPath,
      captionPath,
      approvalPath,
      ledgerPath,
      instagramHandle: profile.handle,
      instagramAccountsPath: profile.accountsPath,
      instagramSettingsPath: profile.settingsPath,
      instagramCredentialsPath: profile.credentialsPath,
      instagramProfileStatePath: profile.stateDir,
      postizToken,
      tiktokIntegration,
    });
  } catch (error) {
    if (error && typeof error === "object") error.unknownEffect = true;
    throw error;
  }
  if (!validDistributionResult(result, contract)) {
    const error = new Error("marketing daily provider result contract mismatch");
    error.unknownEffect = true;
    throw error;
  }
  if (!validProviderJoinKeys(result)) {
    const error = new Error("marketing daily provider metric join keys are missing");
    error.unknownEffect = true;
    throw error;
  }
  return {
    receipt: {
      schema_version: 1,
      kind: "marketing_daily_distribution",
      status: "published",
      creative_id: creativeId,
      platform,
      video_sha256: contract.videoSha256,
      caption_sha256: contract.captionSha256,
      public_url: result.public_url,
      provider_post_id: result.provider_post_id,
      provider_route: result.provider_route,
      provider_reconciled: result.provider_reconciled === true,
      published_at: services.now(),
    },
    result,
  };
}

function readLedgerRows(ledgerPath) {
  try {
    return fs.readFileSync(ledgerPath, "utf8")
      .split(/\r?\n/)
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw new Error("marketing daily distribution ledger is invalid");
  }
}

function receiptFromRows(rows, contract, now) {
  const matching = rows.filter((row) => (
    row
    && row.status === "published"
    && row.creative_id === contract.creativeId
    && row.video_sha256 === contract.videoSha256
    && row.caption_sha256 === contract.captionSha256
    && row.platform === contract.platform
  ));
  const pattern = contract.platform === "instagram" ? INSTAGRAM_URL : TIKTOK_URL;
  const published = matching.filter((row) => pattern.test(String(row.public_url || ""))).at(-1);
  if (!published) return { state: "absent" };
  const publishedAt = validIso(published.ts) ? published.ts : now();
  const provider = (
    PROVIDER_POST_ID.test(String(published.provider_id || ""))
    && PROVIDER_ROUTES.has(published.route)
  ) ? {
      provider_post_id: published.provider_id,
      provider_route: published.route,
    } : {};
  return {
    state: "present",
    receipt: {
      schema_version: 1,
      kind: "marketing_daily_distribution",
      status: "published",
      creative_id: contract.creativeId,
      platform: contract.platform,
      video_sha256: contract.videoSha256,
      caption_sha256: contract.captionSha256,
      public_url: published.public_url,
      ...provider,
      provider_reconciled: true,
      published_at: publishedAt,
    },
  };
}

function createMarketingDailyLoopAdapter(deps = {}) {
  return Object.freeze({
    async plan(context = {}) {
      const platforms = context.platform == null
        ? ["instagram", "tiktok"]
        : [context.platform];
      return platforms.map((platform) => buildMarketingDailyJob({
        ...context,
        platform,
      }));
    },
    execute(job, services = {}) {
      return executeMarketingDailyJob(job, { ...deps, ...services });
    },
    async reconcile(effect) {
      const contract = effectContract(effect && effect.effectKey);
      const services = defaultServices(deps);
      return receiptFromRows(
        readLedgerRows(services.ledgerPath(effect.tenantId)),
        contract,
        services.now,
      );
    },
    verify: verifyMarketingDailyReceipt,
    report: safeMarketingDailySummary,
  });
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  buildMarketingDailyJob,
  createMarketingDailyLoopAdapter,
  executeMarketingDailyJob,
  safeMarketingDailySummary,
  verifyMarketingDailyReceipt,
};
