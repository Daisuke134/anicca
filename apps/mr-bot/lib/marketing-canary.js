"use strict";

const {
  verifyMarketingVideoPublicationReceipt,
} = require("./marketing-video-publication-adapter.js");
const { buildMarketingLivenessJob } = require("./marketing-liveness-adapter.js");
const {
  createMarketingLocalLedger,
  SHADOW_HOLD_AVAILABLE_AT: LOCAL_SHADOW_HOLD_AVAILABLE_AT,
} = require("./marketing-local-ledger.js");

const SHADOW_HOLD_AVAILABLE_AT = LOCAL_SHADOW_HOLD_AVAILABLE_AT;
const PROMOTION_CONFIRMATION = "PROMOTE_HONNE_EN_TIKTOK_CANARY";
const CANARY_LEASE_SECONDS = 180;

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function localStore(options = {}) {
  const store = options.store || options.ledger;
  if (store) {
    for (const method of ["promoteJob", "claimJob"]) {
      if (typeof store[method] !== "function") throw new Error("Honne EN canary local store is unavailable");
    }
    return store;
  }
  return createMarketingLocalLedger({
    dataDir: options.dataDir,
    env: options.env,
    now: options.now,
  });
}

async function promoteHonneEnTikTokCanary(options = {}) {
  if (options.confirmation !== PROMOTION_CONFIRMATION) {
    throw new Error("Honne EN canary promotion confirmation is invalid");
  }
  const tenantId = required(options.tenantId, "Honne EN canary tenant");
  const jobId = required(options.jobId, "Honne EN canary job id");
  const store = localStore(options);
  try {
    return await store.promoteJob({
      tenantId,
      jobId,
      confirmation: PROMOTION_CONFIRMATION,
    });
  } catch (error) {
    if (/confirmation/i.test(String(error && error.message))) throw error;
    throw new Error("Honne EN canary job is not an eligible shadow TikTok job", { cause: error });
  }
}

async function claimExactCanaryJob(options = {}) {
  const tenantId = required(options.tenantId, "canary claim tenant");
  const jobId = required(options.jobId, "canary claim job id");
  const capability = required(options.capability, "canary claim capability");
  const workerId = required(options.workerId, "canary claim worker id");
  const leaseSeconds = Number(options.leaseSeconds || CANARY_LEASE_SECONDS);
  if (!Number.isInteger(leaseSeconds) || leaseSeconds < 30 || leaseSeconds > 900) {
    throw new Error("canary claim lease is invalid");
  }
  const result = await localStore(options).claimJob({
    tenantId,
    jobId,
    capability,
    workerId,
    leaseSeconds,
  });
  if (!result) {
    throw new Error("canary did not claim exactly the selected job");
  }
  return result;
}

async function verifyDirectPublicUrl(url, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") throw new Error("canary URL verifier is unavailable");
  const requested = parseDirectTikTokUrl(url);
  if (requested.handle !== "honne_reveal") {
    throw new Error("Honne EN canary direct TikTok URL account is not @honne_reveal");
  }
  const response = await fetchImpl(url, {
    method: "GET",
    redirect: "follow",
    headers: { "user-agent": "Mr.bot-canary/1.0" },
    signal: AbortSignal.timeout(15_000),
  });
  if (!response || response.status < 200 || response.status >= 300) {
    throw new Error("Honne EN canary direct TikTok URL is not publicly reachable");
  }
  const finalUrl = parseDirectTikTokUrl(response.url);
  if (requested.handle !== "honne_reveal" || finalUrl.handle !== requested.handle) {
    throw new Error("Honne EN canary direct TikTok URL account changed");
  }
  if (finalUrl.postId !== requested.postId) {
    throw new Error("Honne EN canary direct TikTok URL redirect changed the video");
  }
  return { status: response.status, url: response.url };
}

function parseDirectTikTokUrl(value) {
  let parsed;
  try { parsed = new URL(String(value || "")); } catch { throw new Error("Honne EN canary direct TikTok URL is invalid"); }
  if (
    parsed.protocol !== "https:"
    || parsed.hostname !== "www.tiktok.com"
    || parsed.port
    || parsed.username
    || parsed.password
    || parsed.search
    || parsed.hash
  ) {
    throw new Error("Honne EN canary direct TikTok URL is invalid");
  }
  const match = /^\/@([^/]+)\/video\/(\d+)\/?$/.exec(parsed.pathname);
  if (!match) throw new Error("Honne EN canary direct TikTok URL is invalid");
  return { handle: match[1], postId: match[2] };
}

function buildHonneEnCanaryTelegramJob(options = {}) {
  const tenantId = required(options.tenantId, "Honne EN canary tenant");
  const receipt = options.receipt;
  if (
    !verifyMarketingVideoPublicationReceipt(receipt)
    || receipt.product_id !== "honne-ai"
    || receipt.locale !== "en"
    || receipt.platform !== "tiktok"
    || receipt.provider_reconciled !== true
    || !/^https:\/\/www\.tiktok\.com\/@honne_reveal\/video\/\d+\/?$/.test(receipt.public_url)
  ) {
    throw new Error("Honne EN canary publication receipt is not reconciled");
  }
  return buildMarketingLivenessJob({
    tenantId,
    telegramTokenRef: options.telegramTokenRef || "secret://telegram/bot-token",
    telegramChatRef: options.telegramChatRef || "telegram-chat://owner",
    payload: {
      lane: "honne-en-canary",
      product: receipt.product_id,
      locale: receipt.locale,
      platform: receipt.platform,
      slot: receipt.slot,
      status: "published",
      public_url: receipt.public_url,
      retry_state: "not_required",
    },
  });
}

module.exports = {
  PROMOTION_CONFIRMATION,
  CANARY_LEASE_SECONDS,
  SHADOW_HOLD_AVAILABLE_AT,
  buildHonneEnCanaryTelegramJob,
  claimExactCanaryJob,
  createMarketingLocalLedger,
  promoteHonneEnTikTokCanary,
  verifyDirectPublicUrl,
};
