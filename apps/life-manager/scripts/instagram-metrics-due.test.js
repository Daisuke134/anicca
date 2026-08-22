"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { EXPECTED } = require("./instagram-metrics-read.js");
const { runDue } = require("./instagram-metrics-due.js");

test("due planner records missed 2h as unavailable and leaves later windows pending", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-due-")); let sends = 0;
  const env = { LM_DATA_DIR: dataDir, LM_TELEGRAM_BOT_TOKEN: "fake", LM_TELEGRAM_ALERT_CHAT_ID: "fake" };
  const originalFetch = global.fetch; global.fetch = async () => ({ ok: true, json: async () => ({ ok: true, result: { message_id: ++sends } }) });
  try {
    const result = await runDue(Date.parse(EXPECTED.published_at) + 23 * 3600_000, env);
    assert.equal(result.find((row) => row.window === "2h").state, "source_delayed");
    assert.equal(result.find((row) => row.window === "24h").state, "pending");
    assert.equal(result.find((row) => row.window === "daily").state, "reported");
    assert.equal(sends, 2);
    const replay = await runDue(Date.parse(EXPECTED.published_at) + 23 * 3600_000, env);
    assert.equal(replay.find((row) => row.window === "2h").state, "complete");
    assert.equal(replay.find((row) => row.window === "daily").state, "complete"); assert.equal(sends, 2);
  } finally { global.fetch = originalFetch; }
});
