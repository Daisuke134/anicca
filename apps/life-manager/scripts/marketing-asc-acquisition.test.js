"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { importContentObject } = require("../lib/content-object-store.js");
const { PRODUCTS, pending, persistAscAcquisition, rows, summarize } = require("./marketing-asc-acquisition.js");

test("ASC product totals remain unattributed and unavailable stays null on replay", async () => {
  const parsed = rows("Date\tApp Name\tApp Apple Identifier\tDownload Type\tCounts\n2026-08-20\tDaily Affirmations - Anicca\t6755129214\tFirst-time download\t1\n");
  const anicca = summarize(PRODUCTS[0], parsed, [{ Date: "2026-08-19", "App Name": PRODUCTS[0].app_name, "App Apple Identifier": PRODUCTS[0].app_id, Event: "Impression", "Page Type": "No page", Counts: "9", "Unique Counts": "5" }], []);
  assert.equal(anicca.metrics.first_time_downloads.value, 1);
  assert.equal(anicca.metrics.impressions.value, 9);
  assert.equal(anicca.attribution_status, "unattributed");
  assert.equal(summarize(PRODUCTS[0], [], [], []).metrics.first_time_downloads.value, null);
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-asc-join-"));
  const objectDir = path.join(dataDir, "objects");
  const attributionDir = path.join(dataDir, "tenants/dais-local/marketing/attribution");
  fs.mkdirSync(attributionDir, { recursive: true });
  const lineageFile = path.join(dataDir, "lineage.json");
  const lineage = { rows: [{ product_id: "anicca-ios", account_id: "@anicca.jp", platform: "tiktok", provider_post_id: "post-1", public_url: "https://www.tiktok.com/@anicca.jp/video/1", campaign_id: null }, { product_id: "honne-ai", account_id: "@honne_reveal", platform: "tiktok", provider_post_id: "post-2", public_url: "https://www.tiktok.com/@honne_reveal/video/2", campaign_id: null }] };
  fs.writeFileSync(lineageFile, JSON.stringify(lineage));
  const imported = importContentObject(lineageFile, { objectDir });
  fs.writeFileSync(path.join(attributionDir, "lineage.json"), JSON.stringify({ ...lineage, snapshot_ref: imported.ref }));
  const collector = (product) => product.product_id === "anicca-ios" ? anicca : pending(product);
  const first = await persistAscAcquisition(dataDir, "2026-08-23", collector);
  const replay = await persistAscAcquisition(dataDir, "2026-08-23", collector);
  assert.equal(first.created, true);
  assert.equal(replay.created, false);
  assert.equal(first.snapshot_ref, replay.snapshot_ref);
  assert.equal(first.products[1].metrics.first_time_downloads.value, null);
  assert.ok(first.rows.every((row) => row.acquisition_status === "unattributed"));
});
