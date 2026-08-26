"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { EXPECTED } = require("./instagram-metrics-read.js");
const { discoverExpected, runDue } = require("./instagram-metrics-due.js");

test("due planner records missed 2h as unavailable and leaves later windows pending", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-due-")); let sends = 0;
  const env = { LM_DATA_DIR: dataDir, LM_TELEGRAM_BOT_TOKEN: "fake", LM_TELEGRAM_ALERT_CHAT_ID: "fake" };
  const originalFetch = global.fetch; global.fetch = async () => ({ ok: true, json: async () => ({ ok: true, result: { message_id: ++sends } }) });
  try {
    const result = await runDue(Date.parse(EXPECTED.published_at) + 23 * 3600_000, env, [EXPECTED]);
    assert.equal(result.find((row) => row.window === "2h").state, "source_delayed");
    assert.equal(result.find((row) => row.window === "24h").state, "pending");
    assert.equal(result.find((row) => row.window === "daily").state, "reported");
    assert.equal(sends, 2);
    const replay = await runDue(Date.parse(EXPECTED.published_at) + 23 * 3600_000, env, [EXPECTED]);
    assert.equal(replay.find((row) => row.window === "2h").state, "complete");
    assert.equal(replay.find((row) => row.window === "daily").state, "complete"); assert.equal(sends, 2);
  } finally { global.fetch = originalFetch; }
});

test("future verified Instagram rows are discovered from the LM distribution ledger", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-discovery-"));
  const caption = path.join(dataDir, "caption.txt"); fs.writeFileSync(caption, EXPECTED.caption);
  const digest = require("node:crypto").createHash("sha256").update(fs.readFileSync(caption)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const valid = { ts: EXPECTED.published_at, platform: "instagram", status: "published", provider_reconciled: true, format_id: "reelclaw-card", form: "nudge-card", locale: "ja", provider_id: EXPECTED.provider_post_id, public_url: EXPECTED.public_url, caption_path: caption, caption_sha256: digest };
  const unrelated = [
    { ...valid, locale: "en", provider_id: "cmtunrelatedencard", public_url: "https://www.instagram.com/reel/EnCard123/" },
    { ...valid, format_id: "reelclaw-widget", form: "widget-demo-reel", provider_id: "cmtunrelatedjawidget", public_url: "https://www.instagram.com/reel/JaWidget123/" },
    { ...valid, format_id: "reelclaw-widget", form: "widget-demo-reel", locale: "en", provider_id: "cmtunrelatedenwidget", public_url: "https://www.instagram.com/reel/EnWidget123/" },
  ];
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${unrelated.concat(valid).map(JSON.stringify).join("\n")}\n`);
  assert.deepEqual(discoverExpected(dataDir), [EXPECTED]);
});

test("malformed JA Card rows remain fail-closed after unrelated rows are filtered", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-malformed-discovery-"));
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ platform: "instagram", status: "published", provider_reconciled: true, format_id: "reelclaw-card", form: "nudge-card", locale: "ja", provider_id: "bad-provider", public_url: "https://www.instagram.com/reel/not-a-target/" })}\n`);
  assert.throws(() => discoverExpected(dataDir), /Instagram verified distribution row invalid/);
});

test("verified Obou watercolor Reel is discovered as its exact metric effect", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-obou-discovery-"));
  const caption = "相手の感情は相手のもの。";
  const captionPath = path.join(dataDir, "caption.txt"); fs.writeFileSync(captionPath, caption);
  const captionHash = require("node:crypto").createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const row = { ts: "2026-08-26T04:21:05.630917Z", platform: "instagram", status: "published", provider_reconciled: true,
    format_id: "watercolor", form: "buddhist-self-care-reel", locale: "ja", creative_id: "JA-WATERCOLOR-OBOU-b2772de4303a",
    provider_id: "cmt9l523g02mbp20ybq3lefov", public_url: "https://www.instagram.com/reel/DcfVvIkkWyz/",
    caption_path: captionPath, caption_sha256: captionHash, video_sha256: "b2772de4303acc901f42b43a0b3f4af166ae3daeb5ee7fd24e090e5b62f2b0e8" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify(row)}\n`);
  assert.deepEqual(discoverExpected(dataDir), [{
    tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja", account_id: "@obou.anicca", native_owner: "obou.anicca",
    integration_id: "cmooplxmu04tpmd0y4h3cpk33", provider_post_id: row.provider_id, shortcode: "DcfVvIkkWyz",
    public_url: row.public_url, caption, published_at: row.ts,
  }]);
});

test("verified EN affirmation native-carousel receipt is discovered as an immutable metric effect", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-carousel-discovery-"));
  const caption = "5 affirmations to tell\nyourself every morning... | #anicca #affirmation";
  const captionHash = require("node:crypto").createHash("sha256").update(caption).digest("hex");
  const objectDir = path.join(dataDir, "objects", "sha256"); fs.mkdirSync(objectDir, { recursive: true });
  fs.writeFileSync(path.join(objectDir, captionHash), caption);
  fs.chmodSync(path.join(objectDir, captionHash), 0o600);
  const directory = path.join(dataDir, "tenants/dais-local/marketing/native-carousel-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const receipt = {
    schema_version: 1, kind: "marketing_native_carousel_distribution", status: "published",
    product_id: "anicca-ios", format_id: "larry", form: "affirmation-carousel", locale: "en",
    platform: "instagram", account_id: "@anicca.affirmation",
    integration_ref: "integration://postiz/instagram/cmp9pedr700ttqh0yj8o57fog",
    creative_id: "EN-AFFIRMATION-CAROUSEL-da8d8265",
    pack_sha256: "e23cd41257832d2032fd889bd9a16ec95ea8dc213cdd7a2e3f820fbe1578669e",
    media_sha256: ["da8d8265a1344b68a877d776b0cec5b599dc7b3bbd6abc833fcef06e7416df1f", "4fe9ab673f095d39368744974c677cbb5f8305dc2a9dcd1ef1b4b87759d8b42a", "1af8a8c790a733ff1cedca85aaf3de010671a03f54223205da0fd9575a242840", "d097d7b7254ee0a35c95844a89e1f8d1d644775dea134f960ac5e8cb80d230f9", "71ded59ff8a1de5251e607a6ba808945c85537bfca3fbd7f20c65f2912f00e34", "418ad1907d64e4835939bda677709aace44092a936e8a18a7cb8aeeca7652f4f"],
    media_order_sha256: "4daa5db7eb36b424e46057dbf404c390bf1c5c86d44ef99686c48f84429837f9",
    caption_sha256: captionHash, provider_post_id: "cmt9jm8990291p20y0a2l1xmk", provider_reconciled: true,
    public_url: "https://www.instagram.com/p/DcfQ2-hG3KR/", published_at: "2026-08-26T03:37:17.624Z",
  };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ effect_key: "exact", job_id: "job", receipt })}\n`);
  assert.deepEqual(discoverExpected(dataDir), [{
    tenant_id: "dais-local", product_id: "anicca-ios", locale: "en", account_id: "@anicca.affirmation",
    native_owner: "anicca.ios", integration_id: "cmp9pedr700ttqh0yj8o57fog", provider_post_id: "cmt9jm8990291p20y0a2l1xmk",
    shortcode: "DcfQ2-hG3KR", public_url: "https://www.instagram.com/p/DcfQ2-hG3KR/", caption,
    published_at: "2026-08-26T03:37:17.624Z",
  }]);
});
