"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { importContentObject } = require("../lib/content-object-store.js");
const { persistLineage } = require("./marketing-attribution-lineage.js");

test("exact publication lineage stays unattributed when campaign is unavailable and replays", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-attribution-"));
  const objectDir = path.join(dataDir, "objects");
  const captionFile = path.join(dataDir, "caption.txt");
  const videoFile = path.join(dataDir, "video.mp4");
  fs.writeFileSync(captionFile, "Exact hook\nBody\n");
  fs.writeFileSync(videoFile, "video");
  const caption = importContentObject(captionFile, { objectDir });
  const video = importContentObject(videoFile, { objectDir });
  const url = "https://www.tiktok.com/@account/video/123";
  const receiptDir = path.join(dataDir, "marketing");
  fs.mkdirSync(receiptDir, { recursive: true });
  fs.writeFileSync(path.join(receiptDir, "receipts.jsonl"), `${JSON.stringify({
    job_id: `marketing-video-publication:${"a".repeat(64)}`,
    receipt: { kind: "marketing_video_distribution", status: "published", product_id: "honne-ai", locale: "en", platform: "tiktok", provider_post_id: "post-1", public_url: url, creative_id: "HEN-1", slot: "2026-08-20T00:00:00.000Z", published_at: "2026-08-20T00:01:00.000Z", video_sha256: video.sha256, caption_sha256: caption.sha256 },
  })}\n`);
  const metricDir = path.join(dataDir, "tenants", "dais-local", "marketing", "metrics", "account", "123");
  fs.mkdirSync(metricDir, { recursive: true });
  fs.writeFileSync(path.join(metricDir, "24h.combined.json"), JSON.stringify({ schema_version: 1, kind: "tiktok_combined_metric_snapshot", product_id: "honne-ai", locale: "en", account_id: "@account", integration_id: "integration-1", provider_post_id: "post-1", public_url: url, window: "24h", observed_at: "2026-08-21T00:01:00.000Z" }));

  const first = persistLineage({ dataDir });
  const second = persistLineage({ dataDir });
  assert.equal(first.created, true);
  assert.equal(second.created, false);
  assert.equal(first.snapshot_ref, second.snapshot_ref);
  assert.deepEqual(first.coverage, { included: 1, exact_publication_lineage: 1, campaign_attributed: 0, unattributed: 1, attribution_rate: null, attribution_rate_status: "unavailable", attribution_rate_reason: "campaign_not_configured" });
  assert.equal(first.rows[0].hook_text, "Exact hook");
  assert.equal(first.rows[0].hook_sha256, crypto.createHash("sha256").update("Exact hook").digest("hex"));
  assert.equal(first.rows[0].campaign_id, null);
  assert.equal(first.rows[0].attribution_status, "unattributed");
});

test("lineage reads an Apple campaign token from the exact caption object", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-attribution-campaign-")); const objectDir = path.join(dataDir, "objects"); const captionFile = path.join(dataDir, "caption.txt"); const videoFile = path.join(dataDir, "video.mp4"); fs.writeFileSync(captionFile, "Exact hook\n\nhttps://apps.apple.com/app/id6759667221?pt=93486075&ct=honne_en_base_20260823&mt=8\n"); fs.writeFileSync(videoFile, "video"); const caption = importContentObject(captionFile, { objectDir }); const video = importContentObject(videoFile, { objectDir }); const url = "https://www.tiktok.com/@honne_reveal/video/123";
  const receiptDir = path.join(dataDir, "marketing"); fs.mkdirSync(receiptDir, { recursive: true }); fs.writeFileSync(path.join(receiptDir, "receipts.jsonl"), `${JSON.stringify({ receipt: { kind: "marketing_video_distribution", status: "published", product_id: "honne-ai", locale: "en", platform: "tiktok", provider_post_id: "post-1", public_url: url, creative_id: "HEN-1", slot: "2026-08-20T00:00:00.000Z", published_at: "2026-08-20T00:01:00.000Z", video_sha256: video.sha256, caption_sha256: caption.sha256 } })}\n`); const metricDir = path.join(dataDir, "tenants/dais-local/marketing/metrics/honne_reveal/123"); fs.mkdirSync(metricDir, { recursive: true }); fs.writeFileSync(path.join(metricDir, "24h.combined.json"), JSON.stringify({ kind: "tiktok_combined_metric_snapshot", product_id: "honne-ai", locale: "en", account_id: "@honne_reveal", integration_id: "integration-1", provider_post_id: "post-1", public_url: url, window: "24h", observed_at: "2026-08-21T00:01:00.000Z" }));
  const result = persistLineage({ dataDir }); assert.equal(result.rows[0].campaign_id, "honne_en_base_20260823"); assert.equal(result.rows[0].campaign_status, "configured"); assert.equal(result.rows[0].attribution_status, "partial");
});
