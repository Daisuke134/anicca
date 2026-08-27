"use strict";
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
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

test("daily report stays pending when a fresh post has no metric window yet", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-fresh-daily-"));
  const expected = { ...EXPECTED, shortcode: "DcfzPeRGyUn", published_at: "2026-08-26T08:33:00.000Z" };
  const result = await runDue(Date.parse("2026-08-26T08:45:00.000Z"), { LM_DATA_DIR: dataDir }, [expected]);
  assert.equal(result.find((row) => row.window === "daily").state, "pending");
});

test("future verified Instagram rows are discovered from the LM distribution ledger", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-discovery-"));
  const caption = path.join(dataDir, "caption.txt"); fs.writeFileSync(caption, EXPECTED.caption);
  const digest = require("node:crypto").createHash("sha256").update(fs.readFileSync(caption)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const valid = { ts: EXPECTED.published_at, platform: "instagram", status: "published", provider_reconciled: true, format_id: "reelclaw-card", form: "nudge-card", locale: "ja", provider_id: EXPECTED.provider_post_id, public_url: EXPECTED.public_url, caption_path: caption, caption_sha256: digest };
  const unrelated = [
    { ...valid, locale: "fr", provider_id: "cmtunrelatedencard", public_url: "https://www.instagram.com/reel/EnCard123/" },
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

test("Obou duplicate local receipts for one provider effect count only the first lineage", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-obou-dedupe-"));
  const caption = "相手の感情は相手のもの。";
  const captionPath = path.join(dataDir, "caption.txt"); fs.writeFileSync(captionPath, caption);
  const captionHash = crypto.createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const base = { platform: "instagram", status: "published", provider_reconciled: true, format_id: "watercolor", form: "buddhist-self-care-reel", locale: "ja",
    creative_id: "JA-WATERCOLOR-OBOU-b2772de4303a", provider_id: "cmt9l523g02mbp20ybq3lefov", public_url: "https://www.instagram.com/reel/DcfVvIkkWyz/",
    caption_path: captionPath, caption_sha256: captionHash, video_sha256: "b2772de4303acc901f42b43a0b3f4af166ae3daeb5ee7fd24e090e5b62f2b0e8" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ ...base, ts: "2026-08-26T04:21:05.630Z" })}\n${JSON.stringify({ ...base, ts: "2026-08-26T08:51:07.627Z" })}\n`);
  const found = discoverExpected(dataDir);
  assert.equal(found.length, 1);
  assert.equal(found[0].published_at, "2026-08-26T04:21:05.630Z");
});

test("verified EN Card Reel is discovered for the exact encards metric lane", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-encards-discovery-"));
  const caption = "You know that feeling when\n\n#affirmations #mentalhealth #selfcare #mindfulness #anicca\n";
  const captionPath = path.join(dataDir, "caption.txt"); fs.writeFileSync(captionPath, caption);
  const captionHash = require("node:crypto").createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const row = { ts: "2026-08-26T07:13:53.435Z", platform: "instagram", status: "published", provider_reconciled: true,
    format_id: "reelclaw-card", form: "nudge-card", locale: "en", creative_id: "EN-CARD-V2-e678c823480f",
    provider_id: "cmt9rbish00qylf0yw6gt9ulr", public_url: "https://www.instagram.com/reel/Dcfph70jorc/",
    caption_path: captionPath, caption_sha256: captionHash, video_sha256: "e678c823480f357c2d87b19dad87b8dc2c0355f50c850c3ba0dc19b3d67a5d88" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify(row)}\n`);
  assert.deepEqual(discoverExpected(dataDir), [{
    tenant_id: "dais-local", product_id: "anicca-ios", locale: "en", account_id: "@anicca.encards", native_owner: "anicca.encards",
    integration_id: "cmpc3gx4001nklg0y27a8o66q", provider_post_id: row.provider_id, shortcode: "Dcfph70jorc",
    public_url: row.public_url, caption, published_at: row.ts,
  }]);
});

test("verified EN Widget Reel is discovered for the exact anicca.en metric lane", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-en-widget-discovery-"));
  const caption = "Turn screen time into\nself-belief\n\n#affirmations #mentalhealth #selfcare #mindfulness #anicca\n";
  const captionPath = path.join(dataDir, "caption.txt"); fs.writeFileSync(captionPath, caption);
  const captionHash = require("node:crypto").createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const row = { ts: "2026-08-26T08:00:00.000Z", platform: "instagram", status: "published", provider_reconciled: true,
    format_id: "reelclaw-widget", form: "lockscreen-affirmation-widget", locale: "en", creative_id: "EN-WIDGET-BELIEF-c3b80a8f670d",
    provider_id: "cmtwidgetexact123", public_url: "https://www.instagram.com/reel/ExactWidget1/",
    caption_path: captionPath, caption_sha256: captionHash, video_sha256: "c3b80a8f670df10e4eeb9bcdef5037f86ec552b5b7d389001382564f636e95de" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify(row)}\n`);
  assert.deepEqual(discoverExpected(dataDir), [{
    tenant_id: "dais-local", product_id: "anicca-ios", locale: "en", account_id: "@anicca.en", native_owner: "anicca.en",
    integration_id: "cmn8y95rg02d2qx0y09bbk5pb", provider_post_id: row.provider_id, shortcode: "ExactWidget1",
    public_url: row.public_url, caption, published_at: row.ts,
  }]);
});

test("verified JA Widget Reel is discovered for the exact anicca.jp.videos metric lane", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-ja-widget-discovery-"));
  const caption = "アファメーションを\nロック画面に置いてみた\n\n#ロック画面 #アファメーション #ウィジェット #メンタルヘルス #アニッチャ\n";
  const captionPath = path.join(dataDir, "caption.txt"); fs.writeFileSync(captionPath, caption);
  const captionHash = require("node:crypto").createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true });
  const row = { ts: "2026-08-26T10:00:00.000Z", platform: "instagram", status: "published", provider_reconciled: true,
    format_id: "reelclaw-widget", form: "lockscreen-affirmation-widget", locale: "ja", creative_id: "JA-WIDGET-AFFIRMATION-1315a945e39a",
    provider_id: "cmtjawidgetexact123", public_url: "https://www.instagram.com/reel/ExactJaWidget1/",
    caption_path: captionPath, caption_sha256: captionHash, video_sha256: "1315a945e39aaef07aeccbc8afa7ef8f1fccb28718615cf15b07e2e03434f123" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify(row)}\n`);
  assert.deepEqual(discoverExpected(dataDir), [{
    tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp.videos", native_owner: "anicca.jp.videos",
    integration_id: "cmmzzg2es0539p30ycb94ayx0", provider_post_id: row.provider_id, shortcode: "ExactJaWidget1",
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

test("verified JA Larry production carousel is discovered for automatic metrics", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-larry-ja-discovery-"));
  const caption = "メンタルが勝手に安定する\n口癖５選\n\n#anicca #affirmation";
  const captionHash = crypto.createHash("sha256").update(caption).digest("hex");
  const objectDir = path.join(dataDir, "objects", "sha256"); fs.mkdirSync(objectDir, { recursive: true }); fs.writeFileSync(path.join(objectDir, captionHash), caption, { mode: 0o600 });
  const media = ["d4f0030358eab3c89e36ea938ccfe1a3e33eadcc42d55f269a456fd72de08a3d", "ac47a0fbc783a5bde9160b85da29b513a7e36daa131c252384510753cb210a8f", "bbd5baa7f4463ac7c2d2e814705e702514e28db5f4760023d4fecdf924f0acd5", "366527448cc3b70dbc15cb42b0fc196f572c65b51730efbd6ea1d0c69ec91dae", "7d1ca4ebf4d2ede902ecb3251eefd8ab36fad8e4408133b9463f4edc56e8fc5f", "0525669aca914138a707ae782bb759b74c833eae90ff9cfefb2635a64e6b5a68"];
  const receipt = { schema_version: 1, kind: "marketing_native_carousel_distribution", status: "published", product_id: "anicca-ios", format_id: "larry", form: "affirmation-carousel", locale: "ja", platform: "instagram", account_id: "@ani.cca1234", integration_ref: "integration://postiz/instagram/cmq3sq7mc000eqp0y7azfm8yk", creative_id: "LARRY-JA-CANARY", pack_sha256: "3d6acc97e59f270a403b39a27e070265fc79d0c5d842ede19c64a5be8a9db79e", media_sha256: media, media_order_sha256: crypto.createHash("sha256").update(JSON.stringify(media)).digest("hex"), caption_sha256: captionHash, provider_post_id: "cmt9uc44101hulf0ygsfdkkfv", provider_reconciled: true, public_url: "https://www.instagram.com/p/DcfzPeRGyUn/", published_at: "2026-08-26T08:33:00.000Z" };
  const directory = path.join(dataDir, "tenants/dais-local/marketing/native-carousel-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true }); fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ effect_key: "exact", receipt })}\n`);
  assert.equal(discoverExpected(dataDir).some((row) => row.shortcode === "DcfzPeRGyUn" && row.native_owner === "ani.cca1234"), true);
});

test("metrics owner also emits the permanent cadence reconciliation snapshot", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-cadence-owner-"));
  const result = await runDue(Date.parse("2026-08-27T08:00:00.000Z"), { LM_DATA_DIR: dataDir, LM_MARKETING_CADENCE_REPORT: "0" });
  const cadence = result.find((row) => row.window === "cadence");
  assert.equal(cadence.state, "created");
  assert.equal(cadence.counts.published, 0);
  assert.equal(cadence.counts.missed + cadence.counts.pending, 39);
  assert.ok(cadence.file);
});
