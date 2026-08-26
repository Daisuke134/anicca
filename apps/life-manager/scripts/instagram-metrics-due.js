#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const {
  EN_AFFIRMATION_LANE,
  verifyMarketingNativeCarouselPublicationReceipt,
} = require("../lib/marketing-native-carousel-publication-adapter.js");
const { EXPECTED, collectWindow, persistDailyDigest, persistDelayedSnapshot, sendMetricSnapshot } = require("./instagram-metrics-read.js");

const WINDOWS = Object.freeze({ "2h": 2 * 3600_000, "24h": 24 * 3600_000, "72h": 72 * 3600_000, "7d": 7 * 86400_000 });
const GRACE_MS = 90 * 60_000;
const VIDEO_LANES = Object.freeze([
  Object.freeze({ format_id: "reelclaw-card", form: "nudge-card", locale: "ja", account_id: "@anicca.jp1", native_owner: "anicca.ios.jp", integration_id: "cmn8ycvtn02djqx0ytuisn9mw" }),
  Object.freeze({ format_id: "watercolor", form: "buddhist-self-care-reel", locale: "ja", creative_id: "JA-WATERCOLOR-OBOU-b2772de4303a", video_sha256: "b2772de4303acc901f42b43a0b3f4af166ae3daeb5ee7fd24e090e5b62f2b0e8", account_id: "@obou.anicca", native_owner: "obou.anicca", integration_id: "cmooplxmu04tpmd0y4h3cpk33" }),
]);

function snapshotFile(dataDir, window, expected = EXPECTED) {
  return path.join(dataDir, "tenants", expected.tenant_id, "marketing", "metrics", expected.native_owner, expected.shortcode, `${window}.combined.json`);
}

function discoverExpected(dataDir) {
  const file = path.join(dataDir, "tenants", "dais-local", "marketing", "video-publication", "anicca-ios", "distribution.jsonl");
  const rows = fs.existsSync(file) ? fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line)) : [];
  const found = [];
  for (const row of rows) {
    if (row.platform !== "instagram" || row.status !== "published" || row.provider_reconciled !== true) continue;
    const lane = VIDEO_LANES.find((candidate) => candidate.format_id === row.format_id && candidate.form === row.form && candidate.locale === row.locale
      && (candidate.creative_id === undefined || candidate.creative_id === row.creative_id)
      && (candidate.video_sha256 === undefined || candidate.video_sha256 === row.video_sha256));
    if (!lane) continue;
    const match = /^https:\/\/www\.instagram\.com\/reel\/([A-Za-z0-9_-]+)\/$/.exec(String(row.public_url || ""));
    const captionPath = path.resolve(String(row.caption_path || ""));
    if (!match || !/^c[a-z0-9]+$/.test(String(row.provider_id || "")) || !fs.statSync(captionPath, { throwIfNoEntry: false })?.isFile() || !Number.isFinite(Date.parse(row.ts))) throw new Error("Instagram verified distribution row invalid");
    const caption = fs.readFileSync(captionPath, "utf8");
    if (crypto.createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex") !== row.caption_sha256) throw new Error("Instagram caption object integrity mismatch");
    found.push(Object.freeze({ tenant_id: "dais-local", product_id: "anicca-ios", locale: lane.locale, account_id: lane.account_id, native_owner: lane.native_owner,
      integration_id: lane.integration_id, provider_post_id: row.provider_id, shortcode: match[1], public_url: row.public_url, caption, published_at: row.ts }));
  }
  const carouselFile = path.join(dataDir, "tenants", "dais-local", "marketing", "native-carousel-publication", "anicca-ios", "distribution.jsonl");
  const carouselRows = fs.existsSync(carouselFile) ? fs.readFileSync(carouselFile, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line)) : [];
  for (const row of carouselRows) {
    const receipt = row && row.receipt;
    if (!receipt || receipt.integration_ref !== EN_AFFIRMATION_LANE.integrationRef) continue;
    if (!verifyMarketingNativeCarouselPublicationReceipt(receipt)) throw new Error("Instagram native carousel receipt invalid");
    const match = /^https:\/\/www\.instagram\.com\/p\/([A-Za-z0-9_-]+)\/$/.exec(String(receipt.public_url || ""));
    const integration = /^integration:\/\/postiz\/instagram\/([A-Za-z0-9._:-]+)$/.exec(String(receipt.integration_ref || ""));
    const captionPath = path.join(dataDir, "objects", "sha256", String(receipt.caption_sha256 || ""));
    const captionStat = fs.statSync(captionPath, { throwIfNoEntry: false });
    if (!match || !integration || !/^c[a-z0-9]+$/.test(String(receipt.provider_post_id || ""))
      || !captionStat?.isFile() || (captionStat.mode & 0o077) !== 0 || !Number.isFinite(Date.parse(receipt.published_at))) {
      throw new Error("Instagram verified native carousel row invalid");
    }
    const captionBytes = fs.readFileSync(captionPath);
    if (crypto.createHash("sha256").update(captionBytes).digest("hex") !== receipt.caption_sha256) throw new Error("Instagram caption object integrity mismatch");
    found.push(Object.freeze({ tenant_id: "dais-local", product_id: receipt.product_id, locale: receipt.locale, account_id: receipt.account_id,
      native_owner: EN_AFFIRMATION_LANE.nativeOwner.replace(/^@/, ""), integration_id: integration[1], provider_post_id: receipt.provider_post_id,
      shortcode: match[1], public_url: receipt.public_url, caption: captionBytes.toString("utf8"), published_at: receipt.published_at }));
  }
  const identities = new Set(found.map((row) => `${row.shortcode}\n${row.provider_post_id}`));
  if (identities.size !== found.length) throw new Error("Instagram verified distribution rows ambiguous");
  return found.sort((left, right) => left.published_at.localeCompare(right.published_at));
}

async function runDue(nowMs = Date.now(), env = process.env, provided = null) {
  const dataDir = resolveDataRoot(env); const results = [];
  if (!Number.isFinite(nowMs)) throw new Error("Instagram metrics due clock invalid");
  const expecteds = provided || discoverExpected(dataDir);
  for (const expected of expecteds) {
    const publishedMs = Date.parse(expected.published_at);
    for (const [window, delay] of Object.entries(WINDOWS)) {
      if (fs.existsSync(snapshotFile(dataDir, window, expected))) { results.push({ shortcode: expected.shortcode, window, state: "complete" }); continue; }
      const dueMs = publishedMs + delay;
      if (nowMs < dueMs) { results.push({ shortcode: expected.shortcode, window, state: "pending", due_at: new Date(dueMs).toISOString() }); continue; }
      if (nowMs > dueMs + GRACE_MS) {
        const snapshot = persistDelayedSnapshot({ dataDir, window, observedAt: new Date(nowMs).toISOString(), expected });
        const telegram = await sendMetricSnapshot(snapshot, env, dataDir);
        results.push({ shortcode: expected.shortcode, window, state: "source_delayed", telegram }); continue;
      }
      const observation = await collectWindow(window, env, new Date(nowMs).toISOString(), expected);
      results.push({ shortcode: expected.shortcode, window, state: "measured", telegram: observation.telegram });
    }
    const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(nowMs)).map(({ type, value }) => [type, value]));
    const reportDay = `${parts.year}-${parts.month}-${parts.day}`;
    if (Number(parts.hour) > 17 || (Number(parts.hour) === 17 && Number(parts.minute) >= 30)) {
      const digest = persistDailyDigest({ dataDir, reportDay, observedAt: new Date(nowMs).toISOString(), expected });
      const telegram = await sendMetricSnapshot(digest, env, dataDir);
      results.push({ shortcode: expected.shortcode, window: "daily", state: digest.created ? "reported" : "complete", telegram });
    } else results.push({ shortcode: expected.shortcode, window: "daily", state: "pending", due_at: `${reportDay}T17:30:00+09:00` });
  }
  return results;
}

if (require.main === module) runDue().then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { GRACE_MS, WINDOWS, discoverExpected, runDue, snapshotFile };
