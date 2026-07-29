"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  buildMarketingDailyJob,
  createMarketingDailyLoopAdapter,
  executeMarketingDailyJob,
  safeMarketingDailySummary,
  verifyMarketingDailyReceipt,
} = require("./marketing-daily-adapter.js");
const { importContentObject } = require("./content-object-store.js");

const VIDEO_HASH = "a".repeat(64);
const CAPTION_HASH = "b".repeat(64);
const APPROVAL_HASH = "c".repeat(64);
const IG_URL = "https://www.instagram.com/reel/Portable123/";
const TT_URL = "https://www.tiktok.com/@life_manager/video/7999999999999999999";

function job(platform = "tiktok") {
  return buildMarketingDailyJob({
    tenantId: "tenant-a",
    creativeId: "B01",
    platform,
    videoRef: `object://sha256/${VIDEO_HASH}`,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/life-manager",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/life-manager",
  });
}

test("daily marketing job contains immutable refs only and one content-bound effect key", () => {
  const value = job();

  assert.equal(value.loop_id, "marketing.life-manager.daily");
  assert.equal(value.capability, "marketing.life-manager.daily.publish");
  assert.equal(value.effect_class, "publish");
  assert.equal(value.effect_key, `marketing:life-manager:tiktok:B01:${VIDEO_HASH}:${CAPTION_HASH}`);
  assert.deepEqual(value.input_refs, {
    creative_ref: "creative://life-manager/B01",
    platform_ref: "platform://tiktok",
    video_ref: `object://sha256/${VIDEO_HASH}`,
    caption_ref: `object://sha256/${CAPTION_HASH}`,
    approval_ref: `object://sha256/${APPROVAL_HASH}`,
    instagram_profile_ref: "profile://instagram/life-manager",
    postiz_token_ref: "secret://postiz/api-key",
    tiktok_integration_ref: "integration://postiz/tiktok/life-manager",
  });
  assert.doesNotMatch(JSON.stringify(value), /Users|password|api[_-]?key[^"]*:/i);
});

test("one daily plan creates independent Instagram and TikTok effect jobs", async () => {
  const adapter = createMarketingDailyLoopAdapter({});
  const jobs = await adapter.plan({
    tenantId: "tenant-a",
    creativeId: "B01",
    videoRef: `object://sha256/${VIDEO_HASH}`,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/life-manager",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/life-manager",
  });

  assert.deepEqual(
    jobs.map((value) => value.input_refs.platform_ref),
    ["platform://instagram", "platform://tiktok"],
  );
  assert.equal(new Set(jobs.map((value) => value.effect_key)).size, 2);
});

test("adapter resolves tenant-scoped refs and emits exact clickable public URLs", async () => {
  const calls = [];
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-execute-"));
  const execution = await executeMarketingDailyJob(job(), {
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
          handle: "life_manager",
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
        creative_id: "B01",
        video_sha256: VIDEO_HASH,
        caption_sha256: CAPTION_HASH,
        platform: "tiktok",
        public_url: TT_URL,
        provider_post_id: "postiz-post-B01",
        provider_route: "postiz",
        provider_reconciled: false,
      };
    },
    now: () => "2026-07-29T14:00:00.000Z",
  });

  assert.equal(calls.filter(([kind]) => kind === "object").length, 3);
  assert.deepEqual(execution.receipt, {
    schema_version: 1,
    kind: "marketing_daily_distribution",
    status: "published",
    creative_id: "B01",
    platform: "tiktok",
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
    public_url: TT_URL,
    provider_post_id: "postiz-post-B01",
    provider_route: "postiz",
    provider_reconciled: false,
    published_at: "2026-07-29T14:00:00.000Z",
  });
  assert.doesNotMatch(JSON.stringify(execution.receipt), /provider-token|integration-id|runtime\//);
});

test("adapter rejects a provider result whose hashes or public URLs do not match", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-reject-"));
  const deps = {
    objectStore: { resolve: (ref) => `/objects/${ref.slice(-64)}` },
    profileProvider: {
      get: async () => ({
        handle: "life_manager",
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
      creative_id: "B01",
      video_sha256: "d".repeat(64),
      caption_sha256: CAPTION_HASH,
      platform: "tiktok",
      public_url: TT_URL,
      provider_reconciled: false,
    }),
  };

  await assert.rejects(executeMarketingDailyJob(job(), deps), /result contract/i);
});

test("a new publication without provider metric join keys fails closed", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-provider-"));
  const deps = {
    objectStore: { resolve: (ref) => `/objects/${ref.slice(-64)}` },
    profileProvider: {
      get: async () => ({
        handle: "life_manager",
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
      creative_id: "B01",
      video_sha256: VIDEO_HASH,
      caption_sha256: CAPTION_HASH,
      platform: "tiktok",
      public_url: TT_URL,
      provider_reconciled: false,
    }),
  };

  await assert.rejects(
    executeMarketingDailyJob(job(), deps),
    /provider metric join keys/i,
  );
});

test("each platform reconciles independently by the exact hash pair", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-ledger-"));
  const ledger = path.join(root, "distribution.jsonl");
  const base = {
    creative_id: "B01",
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
    status: "published",
  };
  fs.writeFileSync(ledger, `${JSON.stringify({
    ...base,
    platform: "instagram",
    public_url: IG_URL,
  })}\n`, { mode: 0o600 });
  const adapter = createMarketingDailyLoopAdapter({
    ledgerPath: () => ledger,
  });
  assert.deepEqual(await adapter.reconcile({
    tenantId: "tenant-a",
    effectKey: `marketing:life-manager:tiktok:B01:${VIDEO_HASH}:${CAPTION_HASH}`,
  }), { state: "absent" });

  fs.appendFileSync(ledger, `${JSON.stringify({
    ...base,
    platform: "tiktok",
    public_url: TT_URL,
    provider_id: "postiz-post-B01",
    route: "postiz",
    provider_reconciled: true,
  })}\n`);
  const complete = await adapter.reconcile({
    tenantId: "tenant-a",
    effectKey: `marketing:life-manager:tiktok:B01:${VIDEO_HASH}:${CAPTION_HASH}`,
  });
  assert.equal(complete.state, "present");
  assert.equal(adapter.verify(complete.receipt), true);
  assert.deepEqual(adapter.report(complete.receipt), {
    status: "published",
    creative_id: "B01",
    platform: "tiktok",
    public_url: TT_URL,
    provider_post_id: "postiz-post-B01",
    provider_route: "postiz",
    provider_reconciled: true,
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
  });
});

test("accepts an immutable pre-reconciliation receipt and reports it conservatively", () => {
  const legacyReceipt = {
    schema_version: 1,
    kind: "marketing_daily_distribution",
    status: "published",
    creative_id: "B01",
    platform: "tiktok",
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
    public_url: TT_URL,
    published_at: "2026-07-29T14:00:00.000Z",
  };

  assert.equal(verifyMarketingDailyReceipt(legacyReceipt), true);
  assert.deepEqual(safeMarketingDailySummary(legacyReceipt), {
    status: "published",
    creative_id: "B01",
    platform: "tiktok",
    public_url: TT_URL,
    provider_post_id: null,
    provider_route: null,
    provider_reconciled: false,
    video_sha256: VIDEO_HASH,
    caption_sha256: CAPTION_HASH,
  });
});

test("real content refs are accepted only when imported into the Life Manager object store", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-marketing-objects-"));
  const source = path.join(root, "video.mp4");
  fs.writeFileSync(source, "fixture-video");
  const imported = importContentObject(source, {
    objectDir: path.join(root, "objects"),
  });

  assert.doesNotThrow(() => buildMarketingDailyJob({
    tenantId: "tenant-a",
    creativeId: "A01",
    platform: "instagram",
    videoRef: imported.ref,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/life-manager",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/life-manager",
  }));
});
