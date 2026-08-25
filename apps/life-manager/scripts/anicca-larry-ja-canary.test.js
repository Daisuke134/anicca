"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const {
  ACCOUNT_ID,
  INTEGRATION_REF,
} = require("../lib/marketing-native-carousel-publication-adapter.js");
const {
  parseArgs,
  runAniccaLarryJaCanary,
} = require("./anicca-larry-ja-canary.js");

const SLOT = "2026-08-26T07:30:00.000Z";
const CAPTION = "メンタルが勝手に安定する\n口癖５選\n\n#anicca #affirmation";

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function fixture() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-larry-ja-canary-"));
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") });
  const importBytes = (name, bytes) => {
    const source = path.join(dataDir, name);
    fs.writeFileSync(source, bytes);
    return importContentObject(source, { objectDir: path.join(dataDir, "objects") }).ref;
  };
  const captionRef = importBytes("caption.txt", Buffer.from(CAPTION));
  const mediaRefs = Array.from({ length: 6 }, (_, index) => importBytes(
    `slide-${index + 1}.jpg`,
    Buffer.from([0xff, 0xd8, 0xff, index + 1, 0xff, 0xd9]),
  ));
  const pack = {
    schema_version: 1,
    kind: "marketing_native_carousel_pack",
    product_id: "anicca-ios",
    locale: "ja",
    platform: "instagram",
    account_id: ACCOUNT_ID,
    renderer_id: "larry",
    format_id: "native-photo-carousel",
    form: "affirmation-carousel",
    variant: "ja-v1",
    media_type: "image/jpeg",
    slide_count: 6,
    caption: CAPTION,
    slides: mediaRefs.map((media_ref, index) => ({
      position: index + 1,
      role: index === 0 ? "hook" : "body",
      text: `slide-${index + 1}`,
      media_ref,
    })),
  };
  const packRef = importBytes("pack.json", Buffer.from(JSON.stringify(pack)));
  const approval = {
    schema_version: 1,
    kind: "marketing_native_carousel_publication_approval",
    status: "approved",
    tenant_id: "dais-local",
    product_id: "anicca-ios",
    locale: "ja",
    platform: "instagram",
    account_id: ACCOUNT_ID,
    integration_ref: INTEGRATION_REF,
    pack_ref: packRef,
    media_refs: mediaRefs,
    caption_sha256: captionRef.slice(-64),
  };
  const approvalRef = importBytes("approval.json", Buffer.from(JSON.stringify(approval)));
  const env = {
    LM_DATA_DIR: dataDir,
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_ANICCA_LARRY_JA_PACK_REF: packRef,
    LM_ANICCA_LARRY_JA_MEDIA_REFS: mediaRefs.join(","),
    LM_ANICCA_LARRY_JA_CAPTION_REF: captionRef,
    LM_ANICCA_LARRY_JA_APPROVAL_REF: approvalRef,
    LM_POSTIZ_API_KEY: "postiz-secret-fixture",
    LM_TELEGRAM_BOT_TOKEN: "telegram-secret-fixture",
    LM_TELEGRAM_ALERT_CHAT_ID: "123456789",
  };
  return { dataDir, env, objectStore, importBytes, packRef, mediaRefs, captionRef, approvalRef };
}

function providerCalls(calls, result = {}) {
  return async (input) => {
    calls.push(input);
    return {
      state: "PUBLISHED",
      reconciled: true,
      post_id: "postiz-larry-canary-1",
      post_url: "https://www.instagram.com/p/LarryCanary1/",
      ...result,
    };
  };
}

function verification(fixtureValue, receipt, overrides = {}) {
  const evidenceRef = fixtureValue.importBytes("visual-evidence.txt", Buffer.from("six exact frames verified"));
  return fixtureValue.importBytes("verification.json", Buffer.from(JSON.stringify({
    schema_version: 1,
    kind: "marketing_native_carousel_native_verification",
    status: "verified",
    product_id: "anicca-ios",
    account_id: ACCOUNT_ID,
    integration_ref: INTEGRATION_REF,
    public_url: receipt.public_url,
    pack_sha256: receipt.pack_sha256,
    media_sha256: receipt.media_sha256,
    media_order_sha256: receipt.media_order_sha256,
    caption_sha256: receipt.caption_sha256,
    evidence_ref: evidenceRef,
    verified_at: "2026-08-26T08:00:00.000Z",
    ...overrides,
  })));
}

test("CLI accepts only run with a mandatory exact ISO slot", () => {
  assert.deepEqual(parseArgs(["run", "--slot", SLOT]), { command: "run", slot: SLOT });
  assert.throws(() => parseArgs(["run"]), /usage/i);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage/i);
  assert.throws(() => parseArgs(["publish"]), /usage/i);
});

test("first canary publishes once and holds Telegram without native verification", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const result = await runAniccaLarryJaCanary(["run", "--slot", SLOT], {
    env: value.env,
    runDistribution: providerCalls(publicationCalls),
    sendTelegram: async (...args) => { telegramCalls.push(args); return { ok: true, result: { message_id: 1 } }; },
    now: () => "2026-08-26T07:31:00.000Z",
  });
  assert.deepEqual(result, {
    slot: SLOT,
    publication: { created: true, public_url: "https://www.instagram.com/p/LarryCanary1/", provider_post_id: "postiz-larry-canary-1" },
    telegram: { created: false, held: true, message_id: null },
  });
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 0);
  assert.doesNotMatch(JSON.stringify(result), /postiz-secret|telegram-secret|openclaw|\/Users\//i);
  const jobs = fs.readFileSync(path.join(value.dataDir, "marketing", "jobs.jsonl"), "utf8");
  assert.doesNotMatch(jobs, /postiz-secret|telegram-secret|\/Users\/|openclaw/i);
});

test("tenant and ordered-ref environment bindings are exact", async () => {
  const wrongTenant = fixture();
  wrongTenant.env.LM_RUNTIME_TENANT_ID = "other-tenant";
  await assert.rejects(runAniccaLarryJaCanary(["run", "--slot", SLOT], { env: wrongTenant.env }), /tenant/i);
  const wrongMedia = fixture();
  wrongMedia.env.LM_ANICCA_LARRY_JA_MEDIA_REFS = wrongMedia.mediaRefs.slice(0, 5).join(",");
  await assert.rejects(runAniccaLarryJaCanary(["run", "--slot", SLOT], { env: wrongMedia.env }), /media/i);
});

test("missing or mismatched native verification holds Telegram", async () => {
  const value = fixture();
  const publicationCalls = [];
  const first = await runAniccaLarryJaCanary(["run", "--slot", SLOT], { env: value.env, runDistribution: providerCalls(publicationCalls) });
  value.env.LM_ANICCA_LARRY_JA_NATIVE_VERIFICATION_REF = verification(value, {
    public_url: first.publication.public_url,
    pack_sha256: "f".repeat(64),
    media_sha256: value.mediaRefs.map((ref) => ref.slice(-64)),
    media_order_sha256: sha256(JSON.stringify(value.mediaRefs.map((ref) => ref.slice(-64)))),
    caption_sha256: value.captionRef.slice(-64),
  });
  const held = await runAniccaLarryJaCanary(["run", "--slot", SLOT], { env: value.env, runDistribution: providerCalls(publicationCalls) });
  assert.equal(held.publication.created, false);
  assert.deepEqual(held.telegram, { created: false, held: true, message_id: null });
  assert.equal(publicationCalls.length, 1);
});

test("exact native verification releases one natural Telegram receipt and replay is idempotent", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const options = {
    env: value.env,
    runDistribution: providerCalls(publicationCalls),
    sendTelegram: async (...args) => { telegramCalls.push(args); return { ok: true, result: { message_id: 42 } }; },
    now: () => "2026-08-26T07:31:00.000Z",
  };
  const first = await runAniccaLarryJaCanary(["run", "--slot", SLOT], options);
  const receiptPath = path.join(value.dataDir, "marketing", "receipts.jsonl");
  const publicationReceipt = JSON.parse(fs.readFileSync(receiptPath, "utf8")).receipt;
  value.env.LM_ANICCA_LARRY_JA_NATIVE_VERIFICATION_REF = verification(value, publicationReceipt);
  const replayOptions = { ...options, now: () => "2026-08-26T08:01:00.000Z" };
  const second = await runAniccaLarryJaCanary(["run", "--slot", SLOT], replayOptions);
  const third = await runAniccaLarryJaCanary(["run", "--slot", SLOT], replayOptions);
  assert.equal(first.telegram.held, true);
  assert.deepEqual(second.telegram, { created: true, held: false, message_id: 42 });
  assert.deepEqual(third.telegram, { created: false, held: false, message_id: 42 });
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 1);
});

test("native verification must be strictly after publication and no later than trusted now", async () => {
  const value = fixture();
  const publicationCalls = [];
  const baseOptions = {
    env: value.env,
    runDistribution: providerCalls(publicationCalls),
    now: () => "2026-08-26T07:31:00.000Z",
  };
  await runAniccaLarryJaCanary(["run", "--slot", SLOT], baseOptions);
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  for (const [verifiedAt, trustedNow] of [
    [receipt.published_at, "2026-08-26T08:01:00.000Z"],
    ["2026-08-26T07:30:59.000Z", "2026-08-26T08:01:00.000Z"],
    ["2026-08-26T08:02:00.000Z", "2026-08-26T08:01:00.000Z"],
  ]) {
    value.env.LM_ANICCA_LARRY_JA_NATIVE_VERIFICATION_REF = verification(value, receipt, { verified_at: verifiedAt });
    const held = await runAniccaLarryJaCanary(["run", "--slot", SLOT], { ...baseOptions, now: () => trustedNow });
    assert.equal(held.telegram.held, true);
  }
  value.env.LM_ANICCA_LARRY_JA_NATIVE_VERIFICATION_REF = verification(value, receipt, { verified_at: "2026-08-26T08:00:00.000Z" });
  const released = await runAniccaLarryJaCanary(["run", "--slot", SLOT], { ...baseOptions, now: () => "2026-08-26T08:01:00.000Z", sendTelegram: async () => ({ ok: true, result: { message_id: 77 } }) });
  assert.deepEqual(released.telegram, { created: true, held: false, message_id: 77 });
});

test("a provider result without a direct /p receipt never sends Telegram", async () => {
  const value = fixture();
  const telegramCalls = [];
  await assert.rejects(
    runAniccaLarryJaCanary(["run", "--slot", SLOT], {
      env: value.env,
      runDistribution: providerCalls([], { post_url: "https://www.instagram.com/@ani.cca1234" }),
      sendTelegram: async (...args) => { telegramCalls.push(args); return { ok: true, result: { message_id: 9 } }; },
    }),
    /receipt|provider|publication/i,
  );
  assert.equal(telegramCalls.length, 0);
});
