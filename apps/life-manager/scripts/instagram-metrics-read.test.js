"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { EXPECTED, persistSnapshot } = require("./instagram-metrics-read.js");

const html = `<link rel="canonical" href="${EXPECTED.public_url}" /><meta property="og:description" content="0 likes - ${EXPECTED.native_owner}: &quot;強い人の口癖、5つだけ #anicca #セルフケア #習慣 #AI&quot;" />`;
const postRows = [["Views", 32], ["Reach", 31], ["Saves", 0], ["Likes", 0], ["Comments", 0], ["Shares", 0]].map(([label, total]) => ({ label, data: [{ total: String(total) }] }));

test("Instagram snapshot binds native content, preserves unavailable, and replays", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-metrics-"));
  const input = { dataDir, window: "24h", observedAt: "2026-08-22T12:00:00.000Z", html, accountRows: [], postRows };
  const first = persistSnapshot(input); const replay = persistSnapshot({ ...input, observedAt: "2026-08-22T13:00:00.000Z" });
  assert.equal(first.created, true); assert.equal(replay.created, false);
  assert.equal(first.snapshot.post.views.value, 32); assert.equal(first.snapshot.post.reach.value, 31);
  assert.equal(first.snapshot.post.watch_time.status, "unavailable"); assert.equal(first.snapshot.sources.postiz_account.status, "unavailable");
  assert.equal(fs.statSync(first.file).mode & 0o777, 0o600);
  assert.throws(() => persistSnapshot({ ...input, dataDir: fs.mkdtempSync(path.join(os.tmpdir(), "lm-instagram-metrics-")), html: html.replace(EXPECTED.native_owner, "wrong") }), /mismatch/i);
});
