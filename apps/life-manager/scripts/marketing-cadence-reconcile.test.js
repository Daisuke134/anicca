"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const cadence = require("./marketing-cadence-reconcile.js");

function writeJsonl(file, rows) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
}

function publication(slot, providerPostId, publicUrl) {
  return { schema_version: 1, kind: "marketing_video_distribution", status: "published", product_id: "honne-ai", format_id: "reelclaw", form: "relationship-confession", locale: "ja", platform: "tiktok", slot, creative_id: "HJA-TEST", video_sha256: "1".repeat(64), caption_sha256: "2".repeat(64), provider_post_id: providerPostId, provider_route: "postiz", provider_reconciled: true, public_url: publicUrl, published_at: "2026-08-27T12:00:00.000Z" };
}

test("cadence reconciliation classifies each due slot from launchd schedule and LM receipts", async () => {
  assert.equal(typeof cadence.reconcileCadence, "function");
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-cadence-reconcile-"));
  const route = cadence.ROUTES.find((candidate) => candidate.account === "@honnevideo");
  const slots = ["2026-08-26T23:30:00.000Z", "2026-08-27T03:30:00.000Z", "2026-08-27T12:30:00.000Z"];
  const jobs = slots.map((slot, index) => ({
    job_id: `marketing-video-publication:test-${index}`,
    tenant_id: "dais-local",
    capability: "marketing.video.publish",
    status: "completed",
    input_refs: {
      product_ref: "product://honne-ai",
      locale_ref: "locale://ja",
      platform_ref: "platform://tiktok",
      slot_ref: `schedule-slot://${slot}`,
      tiktok_integration_ref: `integration://postiz/${route.platform}/${route.integration}`,
    },
  }));
  const duplicateJob = { ...jobs[2], job_id: "marketing-video-publication:test-duplicate" };
  writeJsonl(path.join(dataDir, "marketing/jobs.jsonl"), [...jobs, duplicateJob].map((job) => ({ event: "complete", job })));
  writeJsonl(path.join(dataDir, "marketing/receipts.jsonl"), [
    { tenant_id: "dais-local", job_id: jobs[0].job_id, receipt: publication(slots[0], "cmt-first", "https://www.tiktok.com/@honnevideo/video/1") },
    { tenant_id: "dais-local", job_id: jobs[1].job_id, receipt: publication(slots[1], "cmt-second", "https://www.tiktok.com/@honnevideo/video/2") },
    { tenant_id: "dais-local", job_id: jobs[2].job_id, receipt: publication(slots[2], "cmt-third-a", "https://www.tiktok.com/@honnevideo/video/3") },
    { tenant_id: "dais-local", job_id: "marketing-video-publication:test-duplicate", receipt: publication(slots[2], "cmt-third-b", "https://www.tiktok.com/@honnevideo/video/4") },
  ]);
  const result = await cadence.reconcileCadence({
    dataDir,
    nowMs: Date.parse("2026-08-27T12:30:00.000Z"),
    graceMs: 0,
    routes: [route],
    scheduleReader: () => ["08:30", "12:30", "21:30"],
    sendReport: false,
  });
  assert.deepEqual(result.counts, { published: 2, pending: 0, missed: 0, duplicate: 1, explicit_failure: 0 });
  assert.deepEqual(result.routes[0].slots.map((slot) => slot.status), ["published", "published", "duplicate"]);
  assert.equal(fs.existsSync(result.file), true);
  assert.equal(JSON.parse(fs.readFileSync(result.file, "utf8")).counts.duplicate, 1);
  assert.equal(JSON.parse(fs.readFileSync(result.file, "utf8")).product_id, "mobile-marketing");
  assert.equal(JSON.parse(fs.readFileSync(result.file, "utf8")).kind, "marketing_product_metric_summary");
});

test("cadence reconciliation leaves future slots pending and never turns a miss into zero metrics", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-cadence-pending-"));
  const route = cadence.ROUTES.find((candidate) => candidate.account === "@honnevideo");
  const result = await cadence.reconcileCadence({
    dataDir,
    nowMs: Date.parse("2026-08-27T04:00:00.000Z"),
    graceMs: 0,
    routes: [route],
    scheduleReader: () => ["08:30", "12:30", "21:30"],
    sendReport: false,
  });
  assert.equal(result.routes[0].slots[0].status, "missed");
  assert.equal(result.routes[0].slots[1].status, "missed");
  assert.equal(result.routes[0].slots[2].status, "pending");
  assert.equal(result.counts.missed, 2);
  assert.equal(result.metrics, undefined);
});

test("repeating the same cadence state does not create a new snapshot", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-cadence-replay-"));
  const route = cadence.ROUTES.find((candidate) => candidate.account === "@honnevideo");
  const input = { dataDir, nowMs: Date.parse("2026-08-27T04:00:00.000Z"), graceMs: 0, routes: [route], scheduleReader: () => ["08:30", "12:30", "21:30"], sendReport: false };
  const first = await cadence.reconcileCadence(input);
  const replay = await cadence.reconcileCadence({ ...input, nowMs: input.nowMs + 1000 });
  assert.equal(first.created, true);
  assert.equal(replay.created, false);
});

test("cadence soak distinguishes complete healthy days from pending and unhealthy days", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-cadence-soak-")); const route = cadence.ROUTES[0]; const root = path.join(dataDir, "marketing/cadence"); fs.mkdirSync(root, { recursive: true });
  const day = (offset) => new Date(Date.parse("2026-08-28T00:00:00.000Z") - offset * 86400000).toISOString().slice(0, 10);
  for (let offset = 1; offset <= 6; offset += 1) fs.writeFileSync(path.join(root, `${day(offset)}.json`), JSON.stringify({ report_day: day(offset), counts: { published: 3, pending: 0, missed: 0, duplicate: 0, explicit_failure: 0 } }));
  fs.writeFileSync(path.join(root, "2026-08-28.json"), JSON.stringify({ report_day: "2026-08-28", counts: { published: 0, pending: 3, missed: 0, duplicate: 0, explicit_failure: 0 } }));
  const pending = cadence.evaluateCadenceSoak(dataDir, "2026-08-28", [route]); assert.equal(pending.status, "pending"); assert.equal(pending.healthy_days, 6);
  fs.writeFileSync(path.join(root, "2026-08-28.json"), JSON.stringify({ report_day: "2026-08-28", counts: { published: 2, pending: 0, missed: 1, duplicate: 0, explicit_failure: 0 } }));
  const unhealthy = cadence.evaluateCadenceSoak(dataDir, "2026-08-28", [route]); assert.equal(unhealthy.status, "unhealthy"); assert.equal(unhealthy.healthy_days, 6);
});
