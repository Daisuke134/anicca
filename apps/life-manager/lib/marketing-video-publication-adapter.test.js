"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  buildMarketingVideoPublicationJob,
  createMarketingVideoPublicationLoopAdapter,
  verifyMarketingVideoPublicationReceipt,
} = require("./marketing-video-publication-adapter.js");

const VIDEO_HASH = "a".repeat(64);
const CAPTION_HASH = "b".repeat(64);
const APPROVAL_HASH = "c".repeat(64);
const TT_URL = "https://www.tiktok.com/@honne_ai/video/7999999999999999999";

function job(platform = "tiktok") {
  return buildMarketingVideoPublicationJob({
    tenantId: "tenant-a",
    productId: "honne-ai",
    formatId: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T12:30:00.000Z",
    creativeId: "HJA-007-aaaaaaaaaaaa",
    platform,
    videoRef: `object://sha256/${VIDEO_HASH}`,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/honne-ai-ja",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/honne-ai-ja",
  });
}

test("generic video publication job binds product, slot, exact bytes, and one platform effect", () => {
  const value = job();
  const replay = job();

  assert.equal(value.job_id, replay.job_id);
  assert.equal(value.loop_id, "marketing.video.publish");
  assert.equal(value.capability, "marketing.video.publish");
  assert.equal(value.effect_class, "publish");
  assert.equal(
    value.effect_key,
    `marketing:video:honne-ai:tiktok:HJA-007-aaaaaaaaaaaa:${VIDEO_HASH}:${CAPTION_HASH}`,
  );
  assert.deepEqual(value.input_refs, {
    product_ref: "product://honne-ai",
    format_ref: "format://reelclaw",
    form_ref: "form://relationship-confession",
    locale_ref: "locale://ja",
    slot_ref: "schedule-slot://2026-07-30T12:30:00.000Z",
    creative_ref: "creative://honne-ai/HJA-007-aaaaaaaaaaaa",
    platform_ref: "platform://tiktok",
    video_ref: `object://sha256/${VIDEO_HASH}`,
    caption_ref: `object://sha256/${CAPTION_HASH}`,
    approval_ref: `object://sha256/${APPROVAL_HASH}`,
    instagram_profile_ref: "profile://instagram/honne-ai-ja",
    postiz_token_ref: "secret://postiz/api-key",
    tiktok_integration_ref: "integration://postiz/tiktok/honne-ai-ja",
  });
  assert.doesNotMatch(
    JSON.stringify(value),
    /\.openclaw|profitable-claude|\/Users\/|provider-token/,
  );
});

test("adapter plans independent Instagram and TikTok jobs for one product artifact", async () => {
  const adapter = createMarketingVideoPublicationLoopAdapter({});
  const jobs = await adapter.plan({
    tenantId: "tenant-a",
    productId: "honne-ai",
    formatId: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T12:30:00.000Z",
    creativeId: "HJA-007-aaaaaaaaaaaa",
    videoRef: `object://sha256/${VIDEO_HASH}`,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/honne-ai-ja",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/honne-ai-ja",
  });

  assert.deepEqual(
    jobs.map((value) => value.input_refs.platform_ref),
    ["platform://instagram", "platform://tiktok"],
  );
  assert.equal(new Set(jobs.map((value) => value.effect_key)).size, 2);
});

test("adapter publishes through tenant-scoped providers and returns product lineage plus public URL", async () => {
  const calls = [];
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-publish-"));
  const adapter = createMarketingVideoPublicationLoopAdapter({
    objectStore: {
      resolve(ref) {
        calls.push(["object", ref]);
        return `/runtime/objects/${ref.slice(-64)}`;
      },
    },
    profileProvider: {
      async get(tenantId, ref) {
        calls.push(["profile", tenantId, ref]);
        return {
          handle: "honne_ai",
          accountsPath: "/runtime/profiles/accounts.json",
          settingsPath: "/runtime/profiles/settings.json",
          credentialsPath: "/runtime/profiles/credentials.json",
          stateDir: "/runtime/profiles/state",
        };
      },
    },
    secretProvider: {
      async get(tenantId, ref) {
        calls.push(["secret", tenantId, ref]);
        return "provider-token";
      },
    },
    integrationProvider: {
      async get(tenantId, ref) {
        calls.push(["integration", tenantId, ref]);
        return "integration-id";
      },
    },
    ledgerPath: () => path.join(root, "distribution.jsonl"),
    async runDistribution(input) {
      calls.push(["distribution", input]);
      return {
        creative_id: "HJA-007-aaaaaaaaaaaa",
        video_sha256: VIDEO_HASH,
        caption_sha256: CAPTION_HASH,
        platform: "tiktok",
        public_url: TT_URL,
        provider_post_id: "postiz-honne-HJA-007",
        provider_route: "postiz",
        provider_reconciled: false,
      };
    },
    now: () => "2026-07-30T12:30:02.000Z",
  });

  const execution = await adapter.execute(job());

  assert.equal(calls.filter(([kind]) => kind === "object").length, 3);
  assert.deepEqual(execution.receipt, {
    schema_version: 1,
    kind: "marketing_video_distribution",
    status: "published",
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T12:30:00.000Z",
    creative_id: "HJA-007-aaaaaaaaaaaa",
    platform: "tiktok",
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
    public_url: TT_URL,
    provider_post_id: "postiz-honne-HJA-007",
    provider_route: "postiz",
    provider_reconciled: false,
    published_at: "2026-07-30T12:30:02.000Z",
  });
  assert.equal(verifyMarketingVideoPublicationReceipt(execution.receipt), true);
  assert.doesNotMatch(
    JSON.stringify(execution.receipt),
    /provider-token|integration-id|runtime\//,
  );
});

test("adapter rejects a cross-product job or mismatched provider result before completion", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-publish-reject-"));
  const adapter = createMarketingVideoPublicationLoopAdapter({
    objectStore: { resolve: (ref) => `/objects/${ref.slice(-64)}` },
    profileProvider: {
      get: async () => ({
        handle: "honne_ai",
        accountsPath: "/profiles/accounts.json",
        settingsPath: "/profiles/settings.json",
        credentialsPath: "/profiles/credentials.json",
        stateDir: "/profiles/state",
      }),
    },
    secretProvider: { get: async () => "token" },
    integrationProvider: { get: async () => "integration" },
    ledgerPath: () => path.join(root, "distribution.jsonl"),
    runDistribution: async () => ({
      creative_id: "HJA-007-aaaaaaaaaaaa",
      video_sha256: "d".repeat(64),
      caption_sha256: CAPTION_HASH,
      platform: "tiktok",
      public_url: TT_URL,
      provider_post_id: "postiz-honne-HJA-007",
      provider_route: "postiz",
    }),
  });

  await assert.rejects(adapter.execute(job()), /provider result contract/i);
  const forged = {
    ...job(),
    input_refs: {
      ...job().input_refs,
      product_ref: "product://anicca-ios",
    },
  };
  await assert.rejects(adapter.execute(forged), /job contract/i);
});
