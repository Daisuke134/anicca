"use strict";
const assert = require("node:assert/strict"); const fs = require("node:fs"); const os = require("node:os"); const path = require("node:path"); const test = require("node:test");
const crypto = require("node:crypto");
const due = require("./tiktok-metrics-due.js");
const { TARGETS, discoverTarget, discoverTargets, runDue, snapshotFile } = due;
const EXPECTED = { tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp4", native_owner: "anicca.jp4", integration_id: "cmn8x8hdv028uqx0y4gdfse5t", provider_post_id: "cmt328uot00s2qk0y23e8ptii", shortcode: "7676495865816632583", video_id: "7676495865816632583", public_url: "https://www.tiktok.com/@anicca.jp4/video/7676495865816632583", caption: "今すぐやれ", published_at: "2026-08-21T14:46:13.240Z" };

test("existing TikTok snapshots are read-only and never re-enqueued", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-existing-snapshot-"));
  const file = snapshotFile(dataDir, EXPECTED, "2h");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify({ schema_version: 1, kind: "tiktok_combined_metric_snapshot", ...EXPECTED, window: "2h", observed_at: "2026-08-21T17:00:00.000Z" })}\n`);
  const env = { LM_DATA_DIR: dataDir, LM_TELEGRAM_BOT_TOKEN: "fake", LM_TELEGRAM_ALERT_CHAT_ID: "fake" };
  const originalFetch = global.fetch; let sends = 0;
  global.fetch = async () => { sends += 1; return { ok: true, json: async () => ({ ok: true, result: { message_id: sends } }) }; };
  try {
    const result = await runDue(Date.parse(EXPECTED.published_at) + 3 * 3600_000, env, [EXPECTED]);
    const row = result.find((candidate) => candidate.window === "2h");
    assert.equal(row.state, "complete");
    assert.deepEqual(row.telegram, { created: false, reason: "snapshot_replay" });
    assert.equal(sends, 0);
  } finally { global.fetch = originalFetch; }
});

test("native content mismatch becomes explicit unavailable and does not throw", async () => {
  assert.equal(typeof due.collectWindowSafely, "function");
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-tiktok-mismatch-"));
  const observedAt = "2026-08-27T12:35:00.000Z";
  const result = await due.collectWindowSafely({
    dataDir, expected: EXPECTED, window: "24h", observedAt,
    collect: async () => { throw new Error("TikTok native metric content mismatch"); },
  });
  assert.equal(result.state, "source_mismatch");
  assert.equal(result.observation.snapshot.sources.tiktok_native.status, "unavailable");
  assert.equal(result.observation.snapshot.sources.tiktok_native.reason, "native_content_mismatch");
  assert.equal(JSON.parse(fs.readFileSync(result.observation.file, "utf8")).post.views.value, null);
});

test("JP4 due loop reports delayed and daily once while true 24h stays pending", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-jp4-due-")); let sends = 0; const env = { LM_DATA_DIR: dataDir, LM_TELEGRAM_BOT_TOKEN: "fake", LM_TELEGRAM_ALERT_CHAT_ID: "fake" };
  const originalFetch = global.fetch; global.fetch = async () => ({ ok: true, json: async () => ({ ok: true, result: { message_id: ++sends } }) });
  try { const now = Date.parse(EXPECTED.published_at) + 18.5 * 3600_000; const first = await runDue(now, env, [EXPECTED]); assert.equal(first.find((row) => row.window === "2h").state, "source_delayed"); assert.equal(first.find((row) => row.window === "24h").state, "pending"); assert.equal(first.find((row) => row.window === "daily").state, "reported"); assert.equal(sends, 2); const replay = await runDue(now, env, [EXPECTED]); assert.equal(replay.find((row) => row.window === "2h").state, "complete"); assert.equal(replay.find((row) => row.window === "daily").state, "complete"); assert.equal(sends, 2); } finally { global.fetch = originalFetch; }
});

test("discovery keeps verified Honne EN and JA relationship-confession lanes isolated", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-honne-en-due-")); const caption = "I still think about you";
  const captionPath = path.join(dataDir, "objects", "caption"); fs.mkdirSync(path.dirname(captionPath), { recursive: true }); fs.writeFileSync(captionPath, caption);
  const sha = crypto.createHash("sha256").update(caption).digest("hex"); const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/honne-ai"); fs.mkdirSync(directory, { recursive: true });
  const valid = { ts: "2026-08-21T09:48:55.372Z", platform: "tiktok", status: "published", provider_reconciled: true, format_id: "reelclaw", form: "relationship-confession", locale: "en", public_url: "https://www.tiktok.com/@honne_reveal/video/7676419421304425748", provider_id: "cmt2rn5b302jdph0ylu324jb3", caption_path: captionPath, caption_sha256: sha };
  const ja = { ...valid, locale: "ja", public_url: "https://www.tiktok.com/@honnevideo/video/7676425660641889537", provider_id: "cmt2siqgp0009nt0yoi1qz7lf" };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ ...valid, form: "relationship-intent", public_url: "https://www.tiktok.com/@honne_reveal/video/1" })}\n${JSON.stringify(valid)}\n${JSON.stringify(ja)}\n`);
  const found = discoverTargets(dataDir); assert.deepEqual(found.map((row) => [row.account_id, row.locale, row.video_id]), [["@honne_reveal", "en", "7676419421304425748"], ["@honnevideo", "ja", "7676425660641889537"]]); assert.equal(found[0].caption, caption);
});

test("discovery keeps Anicca main and JP4 identities separate", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-anicca-main-due-")); const caption = "強い人の口癖、5つだけ"; const captionPath = path.join(dataDir, "objects", "caption"); fs.mkdirSync(path.dirname(captionPath), { recursive: true }); fs.writeFileSync(captionPath, caption); const sha = crypto.createHash("sha256").update(caption).digest("hex");
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios"); fs.mkdirSync(directory, { recursive: true }); const base = { ts: "2026-08-21T10:10:15.268Z", platform: "tiktok", status: "published", provider_reconciled: true, format_id: "reelclaw-card", form: "nudge-card", locale: "ja", provider_id: "cmt2s158o02kyph0yvht8d8wd", caption_path: captionPath, caption_sha256: sha };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ ...base, public_url: "https://www.tiktok.com/@anicca.jp/video/7676422253638176020" })}\n`);
  const [found] = discoverTargets(dataDir); assert.equal(found.account_id, "@anicca.jp"); assert.equal(found.native_owner, "anicca.jp"); assert.equal(found.integration_id, "cmp9sdev5012voh0y58qs45xc");
});

test("discovery attributes a reused provider row and native URL only to its first video lineage", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-jp4-collision-due-"));
  const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/anicca-ios");
  const objects = path.join(dataDir, "objects/sha256"); fs.mkdirSync(directory, { recursive: true }); fs.mkdirSync(objects, { recursive: true });
  const captions = ["first caption", "second caption"];
  const rows = captions.map((caption, index) => {
    const captionSha = crypto.createHash("sha256").update(caption).digest("hex"); fs.writeFileSync(path.join(objects, captionSha), caption);
    return { ts: `2026-08-23T0${6 + index}:19:03.000Z`, platform: "tiktok", status: "published", provider_reconciled: true,
      creative_id: `JP4-${index}`, video_sha256: `${index + 1}`.repeat(64), caption_path: path.join(objects, captionSha), caption_sha256: captionSha,
      provider_id: "cmt5exlqb00cjqk0yu6q2xftc", public_url: "https://www.tiktok.com/@anicca.jp4/video/7677106804039355656",
      format_id: "reelclaw-card", form: "nudge-card", locale: "ja" };
  });
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${rows.map(JSON.stringify).join("\n")}\n`);
  const found = discoverTarget(dataDir, TARGETS[0]);
  assert.equal(found.length, 1);
  assert.equal(found[0].caption, "first caption");
});

test("HE discovery uses only its exact reconciled durable receipt fallback", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-anicca-he-due-")); const caption = "今すぐやれ\n\n完璧より完了。"; const sha = crypto.createHash("sha256").update(caption).digest("hex"); const object = path.join(dataDir, "objects/sha256", sha); fs.mkdirSync(path.dirname(object), { recursive: true }); fs.writeFileSync(object, caption); const receipts = path.join(dataDir, "marketing/receipts.jsonl"); fs.mkdirSync(path.dirname(receipts), { recursive: true }); fs.writeFileSync(receipts, `${JSON.stringify({ job_id: "wrong", receipt: { public_url: "https://www.tiktok.com/@anicca.he/video/1" } })}\n${JSON.stringify({ job_id: "marketing-video-publication:7732e4c1e7ff88ccad12a0295e6740125f58da2d6e07558e6f9e432bf85349dd", receipt: { status: "published", product_id: "anicca-ios", format_id: "reelclaw-card", form: "nudge-card", locale: "ja", platform: "tiktok", provider_reconciled: true, public_url: "https://www.tiktok.com/@anicca.he/video/7676500512308481296", provider_post_id: "cmt32u9dj00jxqp0yqdh6yi96", caption_sha256: sha, published_at: "2026-08-21T15:02:41.000Z" } })}\n`); const target = TARGETS.find((row) => row.account_id === "@anicca.he"); const [found] = discoverTarget(dataDir, target); assert.equal(found.account_id, "@anicca.he"); assert.equal(found.provider_post_id, "cmt32u9dj00jxqp0yqdh6yi96"); assert.equal(found.caption, caption);
});
