"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  extractPostizAccountMetrics,
  persistTikTokCombinedSnapshot,
  postizPostSource,
} = require("./tiktok-native-metric-source.js");

const accountRows = [
  ["Followers", 4], ["Following", 8], ["Total Likes", 923], ["Videos", 278],
  ["Views", 5650], ["Recent Likes", 42], ["Recent Comments", 0], ["Recent Shares", 0],
].map(([label, total]) => ({ label, data: [{ total: String(total), date: "2026-08-22" }] }));

function input(dataDir, overrides = {}) {
  return {
    dataDir, tenantId: "dais-local", productId: "honne-ai", locale: "ja", account: "@honnevideo",
    integrationId: "cmnit95mg015rrm0ye5vm8dhl", providerPostId: "cmt2siqgp0009nt0yoi1qz7lf",
    videoId: "7676425660641889537", publicUrl: "https://www.tiktok.com/@honnevideo/video/7676425660641889537",
    caption: "夫婦で「怒ってないよ」の本音を翻訳してみた", window: "24h",
    publishedAt: "2026-08-21T10:13:32.920Z", observedAt: "2026-08-22T10:20:00.000Z",
    metrics: { post: { views: { status: "measured", value: 1035 } } },
    postizAccountAnalytics: accountRows, postizPostAnalytics: [], ...overrides,
  };
}

test("combined TikTok snapshot preserves all account metrics and unavailable post source", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-tiktok-combined-"));
  const first = persistTikTokCombinedSnapshot(input(dataDir));
  const replay = persistTikTokCombinedSnapshot(input(dataDir, { observedAt: "2026-08-22T11:00:00.000Z" }));
  assert.equal(first.created, true);
  assert.equal(replay.created, false);
  assert.equal(first.snapshot.account_metrics.recent_views.value, 5650);
  assert.deepEqual(first.snapshot.sources.postiz_post, { status: "unavailable", reason: "empty_response", response: "empty_array" });
  assert.equal(fs.statSync(first.file).mode & 0o777, 0o600);
});

test("combined TikTok snapshot rejects identity changes and malformed provider metrics", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-tiktok-combined-"));
  persistTikTokCombinedSnapshot(input(dataDir));
  assert.throws(() => persistTikTokCombinedSnapshot(input(dataDir, { providerPostId: "wrong-row" })), /replay mismatch/i);
  assert.throws(() => extractPostizAccountMetrics(accountRows.filter((row) => row.label !== "Followers")), /Followers metric invalid/i);
  assert.throws(() => postizPostSource({}), /post analytics invalid/i);
  assert.deepEqual(postizPostSource([{ label: "Views", data: [{ total: "12" }] }]), {
    status: "measured",
    metrics: { views: { status: "measured", value: 12, source: "postiz_post_analytics" } },
  });
});
