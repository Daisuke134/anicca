"use strict";

const {
  verifyMarketingVideoPublicationReceipt,
} = require("./marketing-video-publication-adapter.js");
const { buildMarketingLivenessJob } = require("./marketing-liveness-adapter.js");

const SHADOW_HOLD_AVAILABLE_AT = "9999-12-31T23:59:59.000Z";
const PROMOTION_CONFIRMATION = "PROMOTE_HONNE_EN_TIKTOK_CANARY";
const CANARY_LEASE_SECONDS = 180;

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

async function promoteHonneEnTikTokCanary(options = {}) {
  if (options.confirmation !== PROMOTION_CONFIRMATION) {
    throw new Error("Honne EN canary promotion confirmation is invalid");
  }
  if (typeof options.query !== "function") {
    throw new Error("Honne EN canary promotion store is unavailable");
  }
  const tenantId = required(options.tenantId, "Honne EN canary tenant");
  const jobId = required(options.jobId, "Honne EN canary job id");
  const selected = await options.query(`
    SELECT job_id, tenant_id, capability, effect_class, status, available_at, input_refs
    FROM public.lm_runtime_jobs
    WHERE tenant_id = $1
      AND job_id = $2
      AND capability = 'marketing.video.publish'
      AND effect_class = 'publish'
      AND status = 'queued'
      AND available_at = $3::timestamptz
      AND input_refs->>'product_ref' = 'product://honne-ai'
      AND input_refs->>'locale_ref' = 'locale://en'
      AND input_refs->>'platform_ref' = 'platform://tiktok'
    LIMIT 1
  `, [tenantId, jobId, SHADOW_HOLD_AVAILABLE_AT]);
  if (!selected || selected.rows.length !== 1) {
    throw new Error("Honne EN canary job is not an eligible shadow TikTok job");
  }
  const promoted = await options.query(`
    UPDATE public.lm_runtime_jobs
    SET available_at = clock_timestamp(), updated_at = clock_timestamp()
    WHERE tenant_id = $1
      AND job_id = $2
      AND capability = 'marketing.video.publish'
      AND status = 'queued'
      AND available_at = $3::timestamptz
      AND input_refs->>'product_ref' = 'product://honne-ai'
      AND input_refs->>'locale_ref' = 'locale://en'
      AND input_refs->>'platform_ref' = 'platform://tiktok'
    RETURNING job_id, available_at
  `, [tenantId, jobId, SHADOW_HOLD_AVAILABLE_AT]);
  if (!promoted || promoted.rows.length !== 1) {
    throw new Error("Honne EN canary promotion lost its idempotent claim");
  }
  return promoted.rows[0];
}

async function claimExactCanaryJob(options = {}) {
  if (typeof options.query !== "function") throw new Error("canary claim store is unavailable");
  const tenantId = required(options.tenantId, "canary claim tenant");
  const jobId = required(options.jobId, "canary claim job id");
  const capability = required(options.capability, "canary claim capability");
  const workerId = required(options.workerId, "canary claim worker id");
  const leaseSeconds = Number(options.leaseSeconds || CANARY_LEASE_SECONDS);
  if (!Number.isInteger(leaseSeconds) || leaseSeconds < 30 || leaseSeconds > 900) {
    throw new Error("canary claim lease is invalid");
  }
  const result = await options.query(`
    UPDATE public.lm_runtime_jobs
    SET status = 'running',
        attempt = attempt + 1,
        lease_owner = $4,
        lease_expires_at = clock_timestamp() + make_interval(secs => $5::double precision),
        last_error_code = NULL,
        updated_at = clock_timestamp()
    WHERE tenant_id = $1
      AND job_id = $2
      AND capability = $3
      AND status = 'queued'
      AND available_at <= clock_timestamp()
      AND attempt < max_attempts
    RETURNING *
  `, [tenantId, jobId, capability, workerId, leaseSeconds]);
  if (!result || result.rows.length !== 1) {
    throw new Error("canary did not claim exactly the selected job");
  }
  return result.rows[0];
}

async function verifyDirectPublicUrl(url, fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") throw new Error("canary URL verifier is unavailable");
  const response = await fetchImpl(url, {
    method: "GET",
    redirect: "follow",
    headers: { "user-agent": "Life-Manager-canary/1.0" },
    signal: AbortSignal.timeout(15_000),
  });
  if (!response || response.status < 200 || response.status >= 300) {
    throw new Error("Honne EN canary direct TikTok URL is not publicly reachable");
  }
  return { status: response.status, url };
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
  promoteHonneEnTikTokCanary,
  verifyDirectPublicUrl,
};
