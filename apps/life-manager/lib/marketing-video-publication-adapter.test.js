"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  buildMarketingVideoPublicationJob,
  createMarketingVideoPublicationLoopAdapter,
  runDistributionProcess,
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

// Mirrors exactly what skills/video/lm-distribution/distribute.py::_append_success writes,
// including the FIX 1 lineage fields (format_id/form/locale/slot).
function ledgerRow(overrides = {}) {
  return {
    ts: "2026-07-30T12:30:05.000Z",
    platform: "tiktok",
    status: "published",
    creative_id: "HJA-007-aaaaaaaaaaaa",
    video_path: "/runtime/objects/video.mp4",
    video_sha256: VIDEO_HASH,
    caption_path: "/runtime/objects/caption.txt",
    caption_sha256: CAPTION_HASH,
    public_url: TT_URL,
    provider_id: "postiz-honne-HJA-007",
    route: "postiz",
    provider_cost_usd: null,
    logged_out_readback: null,
    migration_date: null,
    provider_reconciled: false,
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-30T12:30:00.000Z",
    ...overrides,
  };
}

function reconcileAdapter(root) {
  return createMarketingVideoPublicationLoopAdapter({
    ledgerPath: () => path.join(root, "distribution.jsonl"),
    now: () => "2026-07-30T13:00:00.000Z",
  });
}

test("reconcile recovers a receipt from a lineage-complete ledger row that passes verify", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-reconcile-"));
  fs.writeFileSync(
    path.join(root, "distribution.jsonl"),
    `${JSON.stringify(ledgerRow())}\n`,
  );

  const proof = await reconcileAdapter(root).reconcile({
    tenantId: "tenant-a",
    effectKey: job().effect_key,
  });

  assert.equal(proof.state, "present");
  assert.equal(verifyMarketingVideoPublicationReceipt(proof.receipt), true);
  assert.equal(proof.receipt.format_id, "reelclaw");
  assert.equal(proof.receipt.form, "relationship-confession");
  assert.equal(proof.receipt.locale, "ja");
  assert.equal(proof.receipt.slot, "2026-07-30T12:30:00.000Z");
  assert.equal(proof.receipt.published_at, "2026-07-30T12:30:05.000Z");
  // FIX 3: provider_reconciled is propagated from the ledger row, never fabricated.
  assert.equal(proof.receipt.provider_reconciled, false);
});

test("reconcile propagates a true provider_reconciled ledger value", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-reconcile-true-"));
  fs.writeFileSync(
    path.join(root, "distribution.jsonl"),
    `${JSON.stringify(ledgerRow({ provider_reconciled: true }))}\n`,
  );

  const proof = await reconcileAdapter(root).reconcile({
    tenantId: "tenant-a",
    effectKey: job().effect_key,
  });

  assert.equal(proof.state, "present");
  assert.equal(proof.receipt.provider_reconciled, true);
});

test("reconcile reports absent with a reconciler-shaped receipt when no published row exists", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-reconcile-absent-"));

  const proof = await reconcileAdapter(root).reconcile({
    tenantId: "tenant-a",
    effectKey: job().effect_key,
  });

  // FIX 4: effect-reconciler.js requires a receipt object for the absent decision.
  assert.equal(proof.state, "absent");
  assert.ok(proof.receipt && typeof proof.receipt === "object" && !Array.isArray(proof.receipt));
  assert.equal(proof.receipt.lookup, "ledger_no_published_row");
});

test("reconcile returns unknown rather than fabricating lineage for a legacy shadow row", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-reconcile-legacy-"));
  const legacy = ledgerRow();
  delete legacy.format_id;
  delete legacy.form;
  delete legacy.locale;
  delete legacy.slot;
  fs.writeFileSync(path.join(root, "distribution.jsonl"), `${JSON.stringify(legacy)}\n`);

  const proof = await reconcileAdapter(root).reconcile({
    tenantId: "tenant-a",
    effectKey: job().effect_key,
  });

  // The publication is real but its receipt cannot be verified: neither "present"
  // (would certify an unverifiable receipt) nor "absent" (would authorize a retry
  // of an already-performed publish) is honest.
  assert.equal(proof.state, "unknown");
});

test("job_id and effect_key agree: a new slot for the same artifact derives the same job identity", () => {
  const first = job();
  const laterSlot = buildMarketingVideoPublicationJob({
    tenantId: "tenant-a",
    productId: "honne-ai",
    formatId: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    slot: "2026-07-31T09:00:00.000Z",
    creativeId: "HJA-007-aaaaaaaaaaaa",
    platform: "tiktok",
    videoRef: `object://sha256/${VIDEO_HASH}`,
    captionRef: `object://sha256/${CAPTION_HASH}`,
    approvalRef: `object://sha256/${APPROVAL_HASH}`,
    instagramProfileRef: "profile://instagram/honne-ai-ja",
    postizTokenRef: "secret://postiz/api-key",
    tiktokIntegrationRef: "integration://postiz/tiktok/honne-ai-ja",
  });

  // FIX 2: the DB enforces UNIQUE (tenant_id, effect_key) while enqueue only
  // dedupes on job_id — same bytes+caption+platform must always derive the same
  // job_id, or a new slot would raise a raw unique-constraint exception.
  assert.equal(first.effect_key, laterSlot.effect_key);
  assert.equal(first.job_id, laterSlot.job_id);
});

test("a provider failure is wrapped as unknown-effect without mutating the foreign error", async () => {
  const original = new Error("boom");
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-publish-wrap-"));
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
    runDistribution: async () => { throw original; },
  });

  await assert.rejects(adapter.execute(job()), (error) => {
    assert.notEqual(error, original);
    assert.equal(error.unknownEffect, true);
    assert.equal(error.cause, original);
    assert.equal(error.message, "boom");
    return true;
  });
  assert.equal(Object.prototype.hasOwnProperty.call(original, "unknownEffect"), false);
});

test("distribution subprocess receives an allowlisted environment, not the full parent env", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-publish-env-"));
  const stub = path.join(root, "fake-python.js");
  fs.writeFileSync(
    stub,
    "#!/usr/bin/env node\n"
    + "process.stdout.write(JSON.stringify({\n"
    + "  env_keys: Object.keys(process.env),\n"
    + "  postiz: process.env.POSTIZ_API_KEY,\n"
    + "}));\n",
    { mode: 0o755 },
  );
  process.env.LM_FAKE_FLAG = "1";
  process.env.SECRET_CANARY = "leak-me";
  try {
    const result = runDistributionProcess({
      python: stub,
      creativeId: "HJA-007-aaaaaaaaaaaa",
      platform: "tiktok",
      formatId: "reelclaw",
      form: "relationship-confession",
      locale: "ja",
      slot: "2026-07-30T12:30:00.000Z",
      videoPath: "/v",
      captionPath: "/c",
      ledgerPath: "/l",
      approvalPath: "/a",
      instagramHandle: "h",
      instagramAccountsPath: "/aa",
      instagramSettingsPath: "/s",
      instagramCredentialsPath: "/cr",
      instagramProfileStatePath: "/ps",
      tiktokIntegration: "integration-id",
      postizToken: "provider-token",
    });
    assert.equal(result.postiz, "provider-token");
    assert.ok(result.env_keys.includes("PATH"));
    assert.ok(result.env_keys.includes("LM_FAKE_FLAG"));
    assert.ok(!result.env_keys.includes("SECRET_CANARY"));
  } finally {
    delete process.env.LM_FAKE_FLAG;
    delete process.env.SECRET_CANARY;
  }
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
