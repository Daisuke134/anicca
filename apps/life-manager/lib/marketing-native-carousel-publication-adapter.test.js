"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  EN_AFFIRMATION_LANE,
  EN_SLIDESHOW_TIKTOK_LANE,
  buildMarketingNativeCarouselPublicationJob,
  createMarketingNativeCarouselPublicationLoopAdapter,
  executeMarketingNativeCarouselPublicationJob,
  verifyMarketingNativeCarouselPublicationReceipt,
} = require("./marketing-native-carousel-publication-adapter.js");

test("EN slideshow TikTok lane accepts exact Postiz API photo proof without inventing a URL", () => {
  const lane = EN_SLIDESHOW_TIKTOK_LANE;
  const value = buildMarketingNativeCarouselPublicationJob({
    tenantId: "dais-local", productId: lane.productId, formatId: lane.formatId, form: lane.form,
    locale: lane.locale, slot: "2026-08-26T06:00:00.000Z", creativeId: lane.creativeId,
    accountId: lane.accountId, integrationRef: lane.integrationRef, packRef: lane.packRef,
    mediaRefs: lane.mediaRefs, captionRef: lane.captionRef, approvalRef: lane.approvalRef,
    postizTokenRef: lane.tokenRef,
  });
  assert.equal(value.input_refs.platform_ref, "platform://tiktok");
  assert.equal(value.input_refs.tiktok_integration_ref, lane.integrationRef);
  assert.equal(value.input_refs.instagram_integration_ref, undefined);
  const receipt = {
    schema_version: 1, kind: "marketing_native_carousel_distribution", status: "published",
    product_id: lane.productId, format_id: lane.formatId, form: lane.form, locale: lane.locale,
    platform: lane.platform, account_id: lane.accountId, integration_ref: lane.integrationRef,
    creative_id: lane.creativeId, pack_sha256: lane.packRef.slice(-64),
    media_sha256: lane.mediaRefs.map((ref) => ref.slice(-64)),
    media_order_sha256: crypto.createHash("sha256").update(JSON.stringify(lane.mediaRefs.map((ref) => ref.slice(-64)))).digest("hex"),
    caption_sha256: lane.captionRef.slice(-64), provider_post_id: "postiz-tiktok-carousel-1",
    provider_reconciled: true, public_url: "https://www.tiktok.com/@anicca_slideshow/video/7777777777777777777",
    published_at: "2026-08-26T06:01:00.000Z",
  };
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt(receipt), true);
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt({ ...receipt, public_url: "https://www.tiktok.com/@wrong/video/7777777777777777777" }), false);
  const apiReceipt = {
    ...receipt,
    public_url: null,
    provider_state: "PUBLISHED",
    provider_integration_id: lane.integrationId,
    provider_content_sha256: receipt.caption_sha256,
    provider_title: lane.title,
    provider_posting_method: "DIRECT_POST",
    provider_release_id: "p_pub_url~v2.7678198747632977937",
  };
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt(apiReceipt), true);
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt({ ...apiReceipt, provider_state: "QUEUE" }), false);
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt({ ...apiReceipt, provider_content_sha256: "f".repeat(64) }), false);
});

test("EN slideshow TikTok exact pack executes through six ordered JPEGs only", async () => {
  const lane = EN_SLIDESHOW_TIKTOK_LANE;
  const value = buildMarketingNativeCarouselPublicationJob({
    tenantId: "dais-local", productId: lane.productId, formatId: lane.formatId, form: lane.form,
    locale: lane.locale, slot: "2026-08-26T06:00:00.000Z", creativeId: lane.creativeId,
    accountId: lane.accountId, integrationRef: lane.integrationRef, packRef: lane.packRef,
    mediaRefs: lane.mediaRefs, captionRef: lane.captionRef, approvalRef: lane.approvalRef,
    postizTokenRef: lane.tokenRef,
  });
  const objectRoot = path.join(os.homedir(), ".local/state/life-manager/objects/sha256");
  const ledger = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "lm-tiktok-carousel-")), "distribution.jsonl");
  const calls = [];
  const result = await executeMarketingNativeCarouselPublicationJob(value, {
    objectStore: { resolve: (ref) => path.join(objectRoot, ref.slice(-64)) },
    secretProvider: { get: async () => "postiz-secret" }, ledgerPath: ledger,
    runDistribution: async (input) => { calls.push(input); return { state: "PUBLISHED", reconciled: true, post_id: "postiz-tiktok-carousel-1", post_url: "https://www.tiktok.com/@anicca_slideshow/video/7777777777777777777" }; },
    now: () => "2026-08-26T06:01:00.000Z",
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].platform, "tiktok");
  assert.equal(calls[0].title, "PROCRASTINATION ISN'T LAZINESS.");
  assert.equal(calls[0].integrationId, lane.integrationId);
  assert.equal(calls[0].mediaPaths.length, 6);
  assert.deepEqual(result.receipt.media_sha256, lane.mediaRefs.map((ref) => ref.slice(-64)));
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt(result.receipt), true);
});

const EN_ACCOUNT = "@anicca.affirmation";
const EN_INTEGRATION_REF = "integration://postiz/instagram/cmp9pedr700ttqh0yj8o57fog";
const EN_PACK_REF = "object://sha256/e23cd41257832d2032fd889bd9a16ec95ea8dc213cdd7a2e3f820fbe1578669e";
const EN_MEDIA_REFS = [
  "object://sha256/da8d8265a1344b68a877d776b0cec5b599dc7b3bbd6abc833fcef06e7416df1f",
  "object://sha256/4fe9ab673f095d39368744974c677cbb5f8305dc2a9dcd1ef1b4b87759d8b42a",
  "object://sha256/1af8a8c790a733ff1cedca85aaf3de010671a03f54223205da0fd9575a242840",
  "object://sha256/d097d7b7254ee0a35c95844a89e1f8d1d644775dea134f960ac5e8cb80d230f9",
  "object://sha256/71ded59ff8a1de5251e607a6ba808945c85537bfca3fbd7f20c65f2912f00e34",
  "object://sha256/418ad1907d64e4835939bda677709aace44092a936e8a18a7cb8aeeca7652f4f",
];
const EN_CAPTION_REF = "object://sha256/bf90a15a5a615d2bb295c1829f7329f391a870fe4e950c8099972c20bf6e64a0";
const EN_APPROVAL_REF = "object://sha256/7740cd09733d0cb7a5d8f32ff4614c3e07ebae27df0e3eae8bca8df80b968845";

function enJob(overrides = {}) {
  return buildMarketingNativeCarouselPublicationJob({
    tenantId: "tenant-a",
    productId: "anicca-ios",
    formatId: "larry",
    form: "affirmation-carousel",
    locale: "en",
    slot: "2026-08-26T07:30:00.000Z",
    creativeId: "EN-AFFIRMATION-CAROUSEL-da8d8265",
    accountId: EN_ACCOUNT,
    instagramIntegrationRef: EN_INTEGRATION_REF,
    packRef: EN_PACK_REF,
    mediaRefs: EN_MEDIA_REFS,
    captionRef: EN_CAPTION_REF,
    approvalRef: EN_APPROVAL_REF,
    postizTokenRef: "secret://postiz/api-key",
    ...overrides,
  });
}

function sha256Bytes(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

const CAPTION_BYTES = Buffer.from("メンタルが勝手に安定する\n口癖５選\n\n#anicca #affirmation");
const MEDIA_BYTES = [1, 2, 3, 4, 5, 6].map((position) => (
  Buffer.from([0xff, 0xd8, 0xff, position, 0xd9])
));
const MEDIA_REFS = MEDIA_BYTES.map((bytes) => `object://sha256/${sha256Bytes(bytes)}`);
const PACK_OBJECT = {
  schema_version: 1,
  kind: "marketing_native_carousel_pack",
  product_id: "anicca-ios",
  locale: "ja",
  platform: "instagram",
  account_id: "@ani.cca1234",
  renderer_id: "larry",
  format_id: "native-photo-carousel",
  form: "affirmation-carousel",
  variant: "ja-v1",
  media_type: "image/jpeg",
  slide_count: 6,
  caption: "メンタルが勝手に安定する\n口癖５選\n\n#anicca #affirmation",
  slides: [1, 2, 3, 4, 5, 6].map((position) => ({
    position,
    role: position === 1 ? "hook" : "body",
    text: `slide-${position}`,
    media_ref: MEDIA_REFS[position - 1],
  })),
};
const PACK_JSON = JSON.stringify(PACK_OBJECT);
const PACK_REF = `object://sha256/${sha256Bytes(PACK_JSON)}`;
const CAPTION_REF = `object://sha256/${sha256Bytes(CAPTION_BYTES)}`;
const INTEGRATION_REF = "integration://postiz/instagram/cmq3sq7mc000eqp0y7azfm8yk";
const URL = "https://www.instagram.com/p/CAROUSEL123/";
const APPROVAL_TEMPLATE = {
  schema_version: 1,
  kind: "marketing_native_carousel_publication_approval",
  status: "approved",
  tenant_id: "tenant-a",
  product_id: "anicca-ios",
  locale: "ja",
  platform: "instagram",
  account_id: "@ani.cca1234",
  integration_ref: INTEGRATION_REF,
  pack_ref: PACK_REF,
  media_refs: MEDIA_REFS,
  caption_sha256: CAPTION_REF.slice(-64),
};
const APPROVAL_JSON = JSON.stringify(APPROVAL_TEMPLATE);
const APPROVAL_REF = `object://sha256/${sha256Bytes(APPROVAL_JSON)}`;

function job(overrides = {}) {
  return buildMarketingNativeCarouselPublicationJob({
    tenantId: "tenant-a",
    productId: "anicca-ios",
    formatId: "larry",
    form: "affirmation-carousel",
    locale: "ja",
    slot: "2026-08-26T07:30:00.000Z",
    creativeId: "LARRY-JA-001",
    accountId: "@ani.cca1234",
    instagramIntegrationRef: INTEGRATION_REF,
    packRef: PACK_REF,
    mediaRefs: MEDIA_REFS,
    captionRef: CAPTION_REF,
    approvalRef: APPROVAL_REF,
    postizTokenRef: "secret://postiz/api-key",
    ...overrides,
  });
}

function approval(jobValue, overrides = {}) {
  return {
    schema_version: 1,
    kind: "marketing_native_carousel_publication_approval",
    status: "approved",
    tenant_id: jobValue.tenant_id,
    product_id: "anicca-ios",
    locale: "ja",
    platform: "instagram",
    account_id: "@ani.cca1234",
    integration_ref: INTEGRATION_REF,
    pack_ref: PACK_REF,
    media_refs: MEDIA_REFS,
    caption_sha256: CAPTION_REF.slice(-64),
    ...overrides,
  };
}

function fixtureServices(jobValue, overrides = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-carousel-contract-"));
  const files = new Map();
  const write = (ref, bytes) => {
    const hash = ref.slice(-64);
    const file = path.join(root, hash);
    fs.writeFileSync(file, bytes);
    files.set(ref, file);
    return file;
  };
  const packBytes = Buffer.from(PACK_JSON);
  const captionBytes = CAPTION_BYTES;
  // The refs are intentionally synthetic; injected objectStore below verifies the
  // contract's expected paths while the adapter verifies SHA via this fixture's bytes.
  write(jobValue.input_refs.pack_ref, packBytes);
  write(jobValue.input_refs.caption_ref, captionBytes);
  write(jobValue.input_refs.approval_ref, Buffer.from(JSON.stringify(approval(jobValue))));
  for (const [index, ref] of jobValue.input_refs.media_refs.entries()) {
    write(ref, MEDIA_BYTES[index]);
  }
  const ledgerPath = path.join(root, "distribution.jsonl");
  const objectStore = {
    resolve(ref) {
      const file = files.get(ref);
      if (!file) throw new Error(`missing fixture ref ${ref}`);
      return file;
    },
  };
  return {
    root,
    files,
    ledgerPath,
    objectStore,
    secretProvider: { get: async () => "provider-token" },
    now: () => "2026-08-26T07:31:00.000Z",
    ...overrides,
  };
}

test("job binds exact Larry native-carousel refs and deterministic ordered-media effect", () => {
  const value = job();
  assert.equal(value.loop_id, "marketing.video.publish");
  assert.equal(value.capability, "marketing.video.publish");
  assert.equal(value.effect_class, "publish");
  assert.match(value.job_id, /^marketing-native-carousel-publication:[0-9a-f]{64}$/);
  assert.match(value.effect_key, /^marketing:carousel:anicca-ios:LARRY-JA-001:[0-9a-f]{64}:[0-9a-f]{64}:[0-9a-f]{64}$/);
  assert.deepEqual(value.input_refs, {
    product_ref: "product://anicca-ios",
    format_ref: "format://larry",
    form_ref: "form://affirmation-carousel",
    locale_ref: "locale://ja",
    slot_ref: "schedule-slot://2026-08-26T07:30:00.000Z",
    creative_ref: "creative://anicca-ios/LARRY-JA-001",
    platform_ref: "platform://instagram",
    account_ref: "account://instagram/@ani.cca1234",
    instagram_integration_ref: INTEGRATION_REF,
    pack_ref: PACK_REF,
    media_refs: MEDIA_REFS,
    caption_ref: CAPTION_REF,
    approval_ref: APPROVAL_REF,
    postiz_token_ref: "secret://postiz/api-key",
  });
  assert.doesNotMatch(JSON.stringify(value), /\/Users\/|openclaw|provider-token/);
});

test("EN affirmation lane binds exact identity and six media in order", () => {
  assert.ok(EN_AFFIRMATION_LANE);
  assert.equal(EN_AFFIRMATION_LANE.accountId, EN_ACCOUNT);
  const value = enJob();
  assert.deepEqual(value.input_refs.media_refs, EN_MEDIA_REFS);
  assert.equal(value.input_refs.product_ref, "product://anicca-ios");
  assert.equal(value.input_refs.locale_ref, "locale://en");
  assert.equal(value.input_refs.account_ref, "account://instagram/@anicca.affirmation");
  assert.equal(value.input_refs.instagram_integration_ref, EN_INTEGRATION_REF);
  assert.equal(value.input_refs.pack_ref, EN_PACK_REF);
  assert.equal(value.input_refs.caption_ref, EN_CAPTION_REF);
  assert.equal(value.input_refs.approval_ref, EN_APPROVAL_REF);
});

test("EN lane rejects alternate self-consistent references before provider", () => {
  assert.throws(() => enJob({
    packRef: `object://sha256/${"f".repeat(64)}`,
    mediaRefs: EN_MEDIA_REFS.map((_, index) => `object://sha256/${String(index + 1).repeat(64)}`),
    captionRef: `object://sha256/${"e".repeat(64)}`,
    approvalRef: `object://sha256/${"d".repeat(64)}`,
  }), /lane|reference|identity/i);
});

test("changing only ordered media changes effect identity", () => {
  const reversed = job({ mediaRefs: [...MEDIA_REFS].reverse() });
  assert.notEqual(reversed.effect_key, job().effect_key);
  assert.notEqual(reversed.job_id, job().job_id);
});

test("slot-scoped production gives each daily slot one stable effect without changing legacy identity", () => {
  const first = enJob({ slot: "2026-08-26T01:00:00.000Z", slotScopedEffect: true });
  const replay = enJob({ slot: "2026-08-26T01:00:00.000Z", slotScopedEffect: true });
  const second = enJob({ slot: "2026-08-26T06:00:00.000Z", slotScopedEffect: true });
  assert.equal(first.effect_key, replay.effect_key);
  assert.equal(first.job_id, replay.job_id);
  assert.notEqual(first.effect_key, second.effect_key);
  assert.notEqual(first.job_id, second.job_id);
  assert.match(first.effect_key, /^marketing:carousel:anicca-ios:EN-AFFIRMATION-CAROUSEL-da8d8265(?::[0-9a-f]{64}){4}$/);
  assert.match(enJob().effect_key, /^marketing:carousel:anicca-ios:EN-AFFIRMATION-CAROUSEL-da8d8265(?::[0-9a-f]{64}){3}$/);
});

test("builder is pinned to the one account, integration, product, format, locale and form", () => {
  for (const [field, value] of [
    ["productId", "honne-ai"],
    ["formatId", "reelclaw"],
    ["form", "nudge-card"],
    ["locale", "en"],
    ["accountId", "@anicca.encards"],
    ["instagramIntegrationRef", "integration://postiz/instagram/other"],
  ]) {
    assert.throws(() => job({ [field]: value }), /invalid|Larry|account|integration|locale|format/i);
  }
});

test("pack and approval mismatches fail before transport", async () => {
  const value = job();
  let transports = 0;
  for (const change of [
    { pack: { product_id: "wrong-product" } },
    { approval: { media_refs: [...MEDIA_REFS].reverse() } },
  ]) {
    const services = fixtureServices(value, {
      runDistribution: async () => { transports += 1; throw new Error("transport reached"); },
    });
    if (change.pack) {
      const refPath = services.files.get(PACK_REF);
      fs.writeFileSync(refPath, JSON.stringify({ ...JSON.parse(PACK_JSON), ...change.pack }));
    } else {
      const refPath = services.files.get(APPROVAL_REF);
      fs.writeFileSync(refPath, JSON.stringify(approval(value, change.approval)));
    }
    await assert.rejects(
      executeMarketingNativeCarouselPublicationJob(value, services),
      /pack|approval|identity|media|integrity/i,
    );
  }
  assert.equal(transports, 0);
});

test("execute resolves and SHA-checks object refs, then returns verified receipt", async () => {
  const value = job();
  const calls = [];
  const services = fixtureServices(value, {
    runDistribution: async (input) => {
      calls.push(input);
      return {
        state: "PUBLISHED",
        reconciled: true,
        post_id: "postiz-carousel-1",
        post_url: URL,
      };
    },
  });
  const result = await executeMarketingNativeCarouselPublicationJob(value, services);
  assert.equal(result.receipt.kind, "marketing_native_carousel_distribution");
  assert.equal(result.receipt.public_url, URL);
  assert.equal(result.receipt.account_id, "@ani.cca1234");
  assert.equal(result.receipt.integration_ref, INTEGRATION_REF);
  assert.deepEqual(result.receipt.media_sha256, MEDIA_REFS.map((ref) => ref.slice(-64)));
  assert.equal(result.receipt.media_order_sha256, sha256Bytes(JSON.stringify(result.receipt.media_sha256)));
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].mediaPaths.map((file) => path.basename(file)), MEDIA_REFS.map((ref) => ref.slice(-64)));
  assert.equal(calls[0].captionPath.endsWith(CAPTION_REF.slice(-64)), true);
  assert.equal(calls[0].packPath.endsWith(PACK_REF.slice(-64)), true);
  assert.equal(calls[0].token, "provider-token");
});

test("provider errors and result mismatches are unknown effects", async () => {
  const value = job();
  for (const runDistribution of [
    async () => { throw new Error("provider failed"); },
    async () => ({ state: "PUBLISHED", reconciled: false, post_id: "p", post_url: URL }),
    async () => ({ state: "PUBLISHED", reconciled: true, post_id: "p", post_url: "https://www.instagram.com/@ani.cca1234" }),
  ]) {
    const services = fixtureServices(value, { runDistribution });
    await assert.rejects(
      executeMarketingNativeCarouselPublicationJob(value, services),
      (error) => error && error.unknownEffect === true,
    );
  }
});

test("receipt verification requires direct /p URL, provider reconciliation, and all ordered bytes", () => {
  const receipt = {
    schema_version: 1,
    kind: "marketing_native_carousel_distribution",
    status: "published",
    product_id: "anicca-ios",
    format_id: "larry",
    form: "affirmation-carousel",
    locale: "ja",
    platform: "instagram",
    account_id: "@ani.cca1234",
    integration_ref: INTEGRATION_REF,
    creative_id: "LARRY-JA-001",
    pack_sha256: PACK_REF.slice(-64),
    media_sha256: MEDIA_REFS.map((ref) => ref.slice(-64)),
    media_order_sha256: sha256Bytes(JSON.stringify(MEDIA_REFS.map((ref) => ref.slice(-64)))),
    caption_sha256: CAPTION_REF.slice(-64),
    provider_post_id: "postiz-carousel-1",
    provider_reconciled: true,
    public_url: URL,
    published_at: "2026-08-26T07:31:00.000Z",
  };
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt(receipt), true);
  for (const public_url of [
    "https://www.instagram.com/@ani.cca1234",
    "https://www.instagram.com/reel/CAROUSEL123/",
    "https://www.instagram.com/p/12345678901234567890/",
  ]) {
    assert.equal(verifyMarketingNativeCarouselPublicationReceipt({ ...receipt, public_url }), false);
  }
  assert.equal(verifyMarketingNativeCarouselPublicationReceipt({
    ...receipt,
    media_sha256: [...receipt.media_sha256].reverse(),
  }), false);
});

test("reconcile returns present only for the exact row and otherwise stays unknown", async () => {
  const value = job();
  const services = fixtureServices(value);
  const adapter = createMarketingNativeCarouselPublicationLoopAdapter(services);
  const receipt = {
    schema_version: 1,
    kind: "marketing_native_carousel_distribution",
    status: "published",
    product_id: "anicca-ios",
    format_id: "larry",
    form: "affirmation-carousel",
    locale: "ja",
    platform: "instagram",
    account_id: "@ani.cca1234",
    integration_ref: INTEGRATION_REF,
    creative_id: "LARRY-JA-001",
    pack_sha256: PACK_REF.slice(-64),
    media_sha256: MEDIA_REFS.map((ref) => ref.slice(-64)),
    media_order_sha256: sha256Bytes(JSON.stringify(MEDIA_REFS.map((ref) => ref.slice(-64)))),
    caption_sha256: CAPTION_REF.slice(-64),
    provider_post_id: "postiz-carousel-1",
    provider_reconciled: true,
    public_url: URL,
    published_at: "2026-08-26T07:31:00.000Z",
  };
  assert.deepEqual(await adapter.reconcile(value), { state: "unknown" });
  fs.writeFileSync(services.ledgerPath, `${JSON.stringify({ effect_key: "different-effect", receipt })}\n`);
  assert.deepEqual(await adapter.reconcile(value), { state: "unknown" });
  fs.writeFileSync(services.ledgerPath, "not-json\n");
  assert.deepEqual(await adapter.reconcile(value), { state: "unknown" });
  fs.writeFileSync(services.ledgerPath, `${JSON.stringify({ effect_key: value.effect_key, receipt })}\n`);
  const present = await adapter.reconcile(value);
  assert.equal(present.state, "present");
  assert.deepEqual(present.receipt, receipt);
  fs.writeFileSync(services.ledgerPath, `${JSON.stringify({ effect_key: value.effect_key, receipt: { ...receipt, media_sha256: [] } })}\n`);
  assert.deepEqual(await adapter.reconcile(value), { state: "unknown" });
});

test("a provider response loss is unknown on execute and on subsequent reconcile", async () => {
  const value = job();
  const services = fixtureServices(value);
  let providerCall = 0;
  services.runDistribution = async () => {
    providerCall += 1;
    throw new Error("provider accepted request but response was lost");
  };
  await assert.rejects(
    executeMarketingNativeCarouselPublicationJob(value, services),
    (error) => error && error.unknownEffect === true,
  );
  assert.equal(providerCall, 1);
  assert.deepEqual(
    await createMarketingNativeCarouselPublicationLoopAdapter(services).reconcile(value),
    { state: "unknown" },
  );
});
