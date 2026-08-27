#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { zonedSlotInstant } = require("../lib/honne-ja-shadow-schedule.js");
const { verifyMarketingVideoPublicationReceipt } = require("../lib/marketing-video-publication-adapter.js");
const { sendSummary } = require("./marketing-product-summary.js");

const TIME_ZONE = "Asia/Tokyo";
const DEFAULT_GRACE_MS = 90 * 60_000;
const ROUTES = Object.freeze([
  { label: "ai.anicca.life-manager-honne-en", account: "@honne_reveal", integration: "cmoig11ew001zlv0yk6vqo1us", product: "honne-ai", locale: "en", platform: "tiktok" },
  { label: "ai.anicca.life-manager-honne-ja", account: "@honnevideo", integration: "cmnit95mg015rrm0ye5vm8dhl", product: "honne-ai", locale: "ja", platform: "tiktok" },
  { label: "ai.anicca.life-manager-anicca-main-tiktok", account: "@anicca.jp", integration: "cmp9sdev5012voh0y58qs45xc", product: "anicca-ios", locale: "ja", platform: "tiktok" },
  { label: "ai.anicca.life-manager-anicca-main-instagram", account: "@anicca.jp1", integration: "cmn8ycvtn02djqx0ytuisn9mw", product: "anicca-ios", locale: "ja", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-jp4", account: "@anicca.jp4", integration: "cmn8x8hdv028uqx0y4gdfse5t", product: "anicca-ios", locale: "ja", platform: "tiktok" },
  { label: "ai.anicca.life-manager-anicca-he", account: "@anicca.he", integration: "cmq2aoena08bhqp0yx1epjcik", product: "anicca-ios", locale: "ja", platform: "tiktok" },
  { label: "ai.anicca.life-manager-anicca-larry-ja-instagram", account: "@ani.cca1234", integration: "cmq3sq7mc000eqp0y7azfm8yk", product: "anicca-ios", locale: "ja", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-ja-widget-instagram", account: "@anicca.jp.videos", integration: "cmmzzg2es0539p30ycb94ayx0", product: "anicca-ios", locale: "ja", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-en-card-instagram", account: "@anicca.encards", integration: "cmpc3gx4001nklg0y27a8o66q", product: "anicca-ios", locale: "en", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-en-widget-instagram", account: "@anicca.en", integration: "cmn8y95rg02d2qx0y09bbk5pb", product: "anicca-ios", locale: "en", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-en-affirmation-instagram", account: "@anicca.affirmation", integration: "cmp9pedr700ttqh0yj8o57fog", product: "anicca-ios", locale: "en", platform: "instagram" },
  { label: "ai.anicca.life-manager-anicca-en-slideshow-tiktok", account: "@anicca_slideshow", integration: "cmnenjkff01j1pa0ysufmzhfr", product: "anicca-ios", locale: "en", platform: "tiktok" },
  { label: "ai.anicca.life-manager-anicca-obou-instagram", account: "@obou.anicca", integration: "cmooplxmu04tpmd0y4h3cpk33", product: "anicca-ios", locale: "ja", platform: "instagram" },
]);

function localDay(nowMs) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(nowMs)).map(({ type, value }) => [type, value]));
  return { year: Number(parts.year), month: Number(parts.month), day: Number(parts.day), iso: `${parts.year}-${parts.month}-${parts.day}` };
}

function defaultScheduleReader(label, plistDir = path.join(os.homedir(), "Library/LaunchAgents")) {
  const file = path.join(plistDir, `${label}.plist`);
  const result = spawnSync("/usr/bin/plutil", ["-convert", "json", "-o", "-", "--", file], { encoding: "utf8", timeout: 10_000, maxBuffer: 128 * 1024 });
  if (result.status !== 0) throw new Error(`marketing cadence plist read failed for ${label}`);
  const parsed = JSON.parse(result.stdout);
  const entries = Array.isArray(parsed.StartCalendarInterval) ? parsed.StartCalendarInterval : [parsed.StartCalendarInterval];
  return entries.filter(Boolean).map((entry) => `${String(entry.Hour).padStart(2, "0")}:${String(entry.Minute).padStart(2, "0")}`);
}

function readLatestState(dataDir) {
  const jobs = new Map(); const receipts = new Map();
  const jobsFile = path.join(dataDir, "marketing/jobs.jsonl");
  if (fs.existsSync(jobsFile)) for (const line of fs.readFileSync(jobsFile, "utf8").split(/\r?\n/).filter(Boolean)) { try { const row = JSON.parse(line); const job = row.job; if (job?.capability === "marketing.video.publish") jobs.set(job.job_id, job); } catch {} }
  const receiptsFile = path.join(dataDir, "marketing/receipts.jsonl");
  if (fs.existsSync(receiptsFile)) for (const line of fs.readFileSync(receiptsFile, "utf8").split(/\r?\n/).filter(Boolean)) { try { const row = JSON.parse(line); if (row.job_id && row.receipt) receipts.set(row.job_id, row.receipt); } catch {} }
  return { jobs, receipts };
}

function receiptFor(route, slot, state) {
  const integrationRef = `integration://postiz/${route.platform}/${route.integration}`;
  const matches = [];
  for (const job of state.jobs.values()) {
    const refs = job.input_refs || {};
    const routeIntegration = refs[`${route.platform}_integration_ref`] || refs.integration_ref;
    if (job.tenant_id !== "dais-local" || routeIntegration !== integrationRef || refs.slot_ref !== `schedule-slot://${slot}`) continue;
    const receipt = state.receipts.get(job.job_id);
    if (!receipt || receipt.status !== "published" || receipt.provider_reconciled !== true || receipt.product_id !== route.product || receipt.locale !== route.locale || receipt.platform !== route.platform) continue;
    if (!verifyMarketingVideoPublicationReceipt(receipt) && receipt.kind !== "marketing_native_carousel_distribution") continue;
    matches.push(receipt);
  }
  const providers = new Map(matches.map((receipt) => [receipt.provider_post_id, receipt]));
  return [...providers.values()];
}

function writeSnapshot(dataDir, snapshot) {
  const file = path.join(dataDir, "marketing/cadence", `${snapshot.report_day}.json`); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const existing = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : null;
  if (existing && crypto.createHash("sha256").update(JSON.stringify(existing)).digest("hex") === crypto.createHash("sha256").update(JSON.stringify(snapshot)).digest("hex")) return { created: false, file, snapshot: existing };
  const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`; fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" }); fs.renameSync(temporary, file); fs.chmodSync(file, 0o600); return { created: true, file, snapshot };
}

async function reconcileCadence({ dataDir, nowMs = Date.now(), graceMs = DEFAULT_GRACE_MS, routes = ROUTES, scheduleReader = (label) => defaultScheduleReader(label), env = process.env, sendReport = true } = {}) {
  if (!Number.isFinite(nowMs) || !Number.isFinite(graceMs) || graceMs < 0) throw new Error("marketing cadence clock/grace is invalid");
  const day = localDay(nowMs); const cutoff = nowMs - graceMs; const state = readLatestState(dataDir); const outputRoutes = []; const counts = { published: 0, pending: 0, missed: 0, duplicate: 0, explicit_failure: 0 };
  for (const route of routes) {
    const slots = scheduleReader(route.label).map(String).sort(); const outputSlots = [];
    for (const clock of slots) {
      const slot = zonedSlotInstant(day, clock, TIME_ZONE); const slotMs = Date.parse(slot); const receipts = receiptFor(route, slot, state); let status = "pending"; let providerPostId = null;
      if (slotMs <= cutoff) {
        if (receipts.length === 1) { status = "published"; providerPostId = receipts[0].provider_post_id; }
        else if (receipts.length > 1) status = "duplicate";
        else {
          const integrationRef = `integration://postiz/${route.platform}/${route.integration}`; const jobs = [...state.jobs.values()].filter((job) => job.tenant_id === "dais-local" && (job.input_refs || {})[`${route.platform}_integration_ref`] === integrationRef && (job.input_refs || {}).slot_ref === `schedule-slot://${slot}`);
          status = jobs.some((job) => job.status === "failed" && job.unknown_effect === true) ? "explicit_failure" : "missed";
        }
      }
      counts[status] += 1; outputSlots.push({ slot, clock, status, ...(providerPostId ? { provider_post_id: providerPostId } : {}) });
    }
    outputRoutes.push({ label: route.label, account: route.account, platform: route.platform, integration: route.integration, slots: outputSlots });
  }
  const message = `Life Manager::: ${day.iso} mobile marketing cadenceです。Published ${counts.published}、Pending ${counts.pending}、Missed ${counts.missed}、Duplicate ${counts.duplicate}、Explicit failure ${counts.explicit_failure}。${outputRoutes.map((route) => `${route.account}: ${route.slots.map((slot) => `${slot.clock}=${slot.status}`).join(", ")}`).join(" / ")}。Miss/duplicateは次回slotで自動再確認し、取得不可を0にはしません。`;
  const result = writeSnapshot(dataDir, { schema_version: 1, kind: "marketing_product_metric_summary", period: "daily", product_id: "mobile-marketing", report_key: `cadence-${day.iso}`, report_day: day.iso, observed_at: new Date(nowMs).toISOString(), source: "launchd_plist_plus_lm_receipts", counts, routes: outputRoutes, source_refs: [], message });
  const telegram = sendReport ? await sendSummary({ created: result.created, file: result.file, snapshot: result.snapshot }, env, dataDir) : null;
  return { ...result.snapshot, file: result.file, created: result.created, telegram };
}

if (require.main === module) reconcileCadence({ dataDir: process.env.LM_DATA_DIR }).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });

module.exports = { DEFAULT_GRACE_MS, ROUTES, defaultScheduleReader, reconcileCadence };
