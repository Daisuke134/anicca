"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createContentObjectStore } = require("../lib/content-object-store.js");
const cycle = require("./honne-en-cycle.js");
const { campaignCaptionRef, enqueuePublication, parseArgs, runSlot } = cycle;

const SLOT = "2026-08-21T11:30:00.000Z";

test("Honne EN campaign caption preserves the exact Apple campaign link", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-honne-campaign-")); const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); const copy = path.join(dataDir, "copy.txt"); fs.writeFileSync(copy, "same hook\n\n#honne\n"); const copyRef = objectStore.import(copy).ref;
  const campaignUrl = "https://apps.apple.com/app/id6759667221?pt=93486075&ct=honne_en_base_20260823&mt=8"; const result = campaignCaptionRef(objectStore, dataDir, copyRef, campaignUrl); const caption = fs.readFileSync(objectStore.resolve(result), "utf8");
  assert.equal(caption, `same hook\n\n#honne\n\n${campaignUrl}\n`); assert.notEqual(result, copyRef);
  assert.throws(() => campaignCaptionRef(objectStore, dataDir, copyRef, campaignUrl.replace("6759667221", "6755129214")), /campaign URL is invalid/);
});

test("Honne EN cycle accepts a manual run timestamp without cadence blocking", () => {
  assert.equal(runSlot(SLOT, Date.parse("2026-08-21T09:00:00.000Z")), SLOT);
  assert.equal(runSlot("2026-08-21T09:00:00.000Z", Date.parse("2026-08-21T09:00:00.000Z")), "2026-08-21T09:00:00.000Z");
  assert.throws(() => runSlot("not-an-instant", Date.now()), /timestamp is invalid/i);
});

test("Honne EN scheduled runs resolve to one exact idempotent slot", () => {
  assert.equal(runSlot(null, Date.parse("2026-08-21T02:45:00.000Z")), "2026-08-21T02:00:00.000Z");
  assert.equal(runSlot(null, Date.parse("2026-08-21T11:45:00.000Z")), "2026-08-21T11:30:00.000Z");
  assert.throws(() => runSlot(null, Date.parse("2026-08-20T21:59:00.000Z")), /no due slot/i);
});

test("Honne EN cycle CLI accepts only the optional slot pair", () => {
  assert.equal(parseArgs(["run"]), null);
  assert.equal(parseArgs(["run", "--slot", SLOT]), SLOT);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage|invalid/i);
  assert.throws(() => parseArgs(["run", "--other", SLOT]), /usage|invalid/i);
});

test("Honne EN cycle reuses an existing publication effect", async () => {
  const job = { job_id: "publication", tenant_id: "dais-local" };
  let enqueues = 0;
  const result = await enqueuePublication({
    readJob: async () => ({ ...job, status: "completed" }),
    enqueueJob: async () => { enqueues += 1; },
  }, job, SLOT);
  assert.equal(result.created, false);
  assert.equal(result.job.status, "completed");
  assert.equal(enqueues, 0);
});

test("Honne EN production publication identity is distinct across days", () => {
  assert.equal(typeof cycle.buildHonneEnPublicationJob, "function");
  const artifact = { form: "relationship-confession", creative_id: "HEN-020-aaaaaaaaaaaa", video_ref: `object://sha256/${"1".repeat(64)}` };
  const captionRef = `object://sha256/${"2".repeat(64)}`;
  const approvalRef = `object://sha256/${"3".repeat(64)}`;
  const first = cycle.buildHonneEnPublicationJob("dais-local", "2026-08-26T11:30:00.000Z", artifact, captionRef, approvalRef);
  const replay = cycle.buildHonneEnPublicationJob("dais-local", "2026-08-26T11:30:00.000Z", artifact, captionRef, approvalRef);
  const nextDay = cycle.buildHonneEnPublicationJob("dais-local", "2026-08-27T11:30:00.000Z", artifact, captionRef, approvalRef);
  assert.equal(first.job_id, replay.job_id);
  assert.notEqual(first.job_id, nextDay.job_id);
  assert.notEqual(first.effect_key, nextDay.effect_key);
});
