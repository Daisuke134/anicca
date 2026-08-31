"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  PROMOTION_CONFIRMATION,
  SHADOW_HOLD_AVAILABLE_AT,
  buildHonneEnCanaryTelegramJob,
  claimExactCanaryJob,
  createMarketingLocalLedger,
  promoteHonneEnTikTokCanary,
  verifyDirectPublicUrl,
} = require("./marketing-canary.js");

const URL = "https://www.tiktok.com/@honne_reveal/video/7999999999999999999";
const HASH = "a".repeat(64);

function receipt(overrides = {}) {
  return {
    schema_version: 1,
    kind: "marketing_video_distribution",
    status: "published",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "en",
    slot: "2026-08-21T02:00:00.000Z",
    creative_id: "HEN-001-aaaaaaaaaaaa",
    platform: "tiktok",
    video_sha256: HASH,
    caption_sha256: HASH,
    public_url: URL,
    provider_post_id: "postiz-7999999999999999999",
    provider_route: "postiz",
    provider_reconciled: true,
    published_at: "2026-08-21T02:01:00.000Z",
    ...overrides,
  };
}

function localLedger() {
  return createMarketingLocalLedger({
    dataDir: fs.mkdtempSync(path.join(os.tmpdir(), "lm-canary-test-")),
    now: () => "2026-08-21T02:00:00.000Z",
  });
}

function publicationJob(overrides = {}) {
  return {
    job_id: "canary-job",
    tenant_id: "dais-local",
    loop_id: "marketing.video",
    capability: "marketing.video.publish",
    effect_class: "publish",
    effect_key: "marketing:video:honne-ai:tiktok:creative:video:caption",
    input_refs: {
      product_ref: "product://honne-ai",
      locale_ref: "locale://en",
      platform_ref: "platform://tiktok",
    },
    max_attempts: 3,
    available_at: SHADOW_HOLD_AVAILABLE_AT,
    ...overrides,
  };
}

test("promotion is exact, one-job, and rejects a second promotion", async () => {
  const store = localLedger();
  await store.enqueueJob(publicationJob());
  const promoted = await promoteHonneEnTikTokCanary({
    store,
    tenantId: "dais-local",
    jobId: "canary-job",
    confirmation: PROMOTION_CONFIRMATION,
  });
  assert.equal(promoted.job_id, "canary-job");
  await assert.rejects(
    promoteHonneEnTikTokCanary({
      store,
      tenantId: "dais-local",
      jobId: "canary-job",
      confirmation: PROMOTION_CONFIRMATION,
    }),
    /eligible shadow TikTok/i,
  );
});

test("Telegram receipt job contains the reconciled direct TikTok URL", () => {
  const job = buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt() });
  assert.equal(job.capability, "marketing.liveness.telegram");
  assert.match(job.input_refs.marketing_liveness_ref, /7999999999999999999/);
  assert.equal(job.effect_class, "message");
});

test("Telegram receipt job refuses an unavailable or unreconciled publication", () => {
  assert.throws(
    () => buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt({ provider_reconciled: false }) }),
    /not reconciled/i,
  );
  assert.throws(
    () => buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt({ public_url: "unavailable" }) }),
    /not reconciled/i,
  );
});

test("exact canary claim updates only the selected eligible job", async () => {
  const store = localLedger();
  await store.enqueueJob(publicationJob({ available_at: "2026-08-21T02:00:00.000Z" }));
  const job = await claimExactCanaryJob({
    store,
    tenantId: "dais-local",
    jobId: "canary-job",
    capability: "marketing.video.publish",
    workerId: "canary-worker",
  });
  assert.equal(job.status, "running");
  assert.equal(job.tenant_id, "dais-local");
  assert.equal(job.capability, "marketing.video.publish");
  await assert.rejects(
    claimExactCanaryJob({
      store,
      tenantId: "dais-local",
      jobId: "canary-job",
      capability: "marketing.video.publish",
      workerId: "second-worker",
    }),
    /did not claim exactly/i,
  );
});

test("direct URL verifier rejects non-public responses and accepts a public response", async () => {
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({ status: 403 })),
    /publicly reachable/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({ status: 302 })),
    /publicly reachable/i,
  );
  const result = await verifyDirectPublicUrl(URL, async () => ({ status: 200, url: URL }));
  assert.equal(result.status, 200);
  assert.equal(result.url, URL);
});

test("direct URL verifier rejects profile, other-video, and external redirects", async () => {
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({
      status: 200,
      url: "https://www.tiktok.com/@honne_reveal",
    })),
    /direct TikTok URL|publicly reachable/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({
      status: 200,
      url: "https://www.tiktok.com/@honne_reveal/video/1234567890",
    })),
    /direct TikTok URL|publicly reachable/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({
      status: 200,
      url: "https://www.tiktok.com/@other_account/video/7999999999999999999",
    })),
    /direct TikTok URL|account/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({
      status: 200,
      url: "https://evil.example/@honne_reveal/video/7999999999999999999",
    })),
    /direct TikTok URL|publicly reachable/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl("https://www.tiktok.com/@honne_reveal", async () => ({
      status: 200,
      url: "https://www.tiktok.com/@honne_reveal",
    })),
    /direct TikTok URL/i,
  );
});
