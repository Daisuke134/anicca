"use strict";
const assert = require("node:assert/strict"); const fs = require("node:fs"); const os = require("node:os"); const path = require("node:path"); const test = require("node:test");
const crypto = require("node:crypto");
const { discoverTargets, runDue } = require("./tiktok-metrics-due.js");
const EXPECTED = { tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp4", native_owner: "anicca.jp4", integration_id: "cmn8x8hdv028uqx0y4gdfse5t", provider_post_id: "cmt328uot00s2qk0y23e8ptii", shortcode: "7676495865816632583", video_id: "7676495865816632583", public_url: "https://www.tiktok.com/@anicca.jp4/video/7676495865816632583", caption: "今すぐやれ", published_at: "2026-08-21T14:46:13.240Z" };

test("JP4 due loop reports delayed and daily once while true 24h stays pending", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-jp4-due-")); let sends = 0; const env = { LM_DATA_DIR: dataDir, LM_TELEGRAM_BOT_TOKEN: "fake", LM_TELEGRAM_ALERT_CHAT_ID: "fake" };
  const originalFetch = global.fetch; global.fetch = async () => ({ ok: true, json: async () => ({ ok: true, result: { message_id: ++sends } }) });
  try { const now = Date.parse(EXPECTED.published_at) + 18.5 * 3600_000; const first = await runDue(now, env, [EXPECTED]); assert.equal(first.find((row) => row.window === "2h").state, "source_delayed"); assert.equal(first.find((row) => row.window === "24h").state, "pending"); assert.equal(first.find((row) => row.window === "daily").state, "reported"); assert.equal(sends, 2); const replay = await runDue(now, env, [EXPECTED]); assert.equal(replay.find((row) => row.window === "2h").state, "complete"); assert.equal(replay.find((row) => row.window === "daily").state, "complete"); assert.equal(sends, 2); } finally { global.fetch = originalFetch; }
});

test("discovery adds only the verified Honne EN relationship-confession lane", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-honne-en-due-")); const caption = "I still think about you";
  const captionPath = path.join(dataDir, "objects", "caption"); fs.mkdirSync(path.dirname(captionPath), { recursive: true }); fs.writeFileSync(captionPath, caption);
  const sha = crypto.createHash("sha256").update(caption).digest("hex"); const directory = path.join(dataDir, "tenants/dais-local/marketing/video-publication/honne-ai"); fs.mkdirSync(directory, { recursive: true });
  const valid = { ts: "2026-08-21T09:48:55.372Z", platform: "tiktok", status: "published", provider_reconciled: true, format_id: "reelclaw", form: "relationship-confession", locale: "en", public_url: "https://www.tiktok.com/@honne_reveal/video/7676419421304425748", provider_id: "cmt2rn5b302jdph0ylu324jb3", caption_path: captionPath, caption_sha256: sha };
  fs.writeFileSync(path.join(directory, "distribution.jsonl"), `${JSON.stringify({ ...valid, form: "relationship-intent", public_url: "https://www.tiktok.com/@honne_reveal/video/1" })}\n${JSON.stringify(valid)}\n`);
  const [found] = discoverTargets(dataDir); assert.equal(found.account_id, "@honne_reveal"); assert.equal(found.product_id, "honne-ai"); assert.equal(found.video_id, "7676419421304425748"); assert.equal(found.caption, caption);
});
