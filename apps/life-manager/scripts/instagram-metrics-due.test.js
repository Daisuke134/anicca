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
