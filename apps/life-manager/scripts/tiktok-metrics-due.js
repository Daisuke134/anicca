#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const { persistDailyDigest, sendMetricSnapshot } = require("./instagram-metrics-read.js");
const { collectTikTokWindow } = require("./tiktok-native-metrics-read.js");
const { persistAniccaDaily, persistHonneDaily, sendSummary } = require("./marketing-product-summary.js");

const WINDOWS = Object.freeze({ "2h": 2 * 3600_000, "24h": 24 * 3600_000, "72h": 72 * 3600_000, "7d": 7 * 86400_000 });
const GRACE_MS = 90 * 60_000;
const TARGETS = Object.freeze([
  Object.freeze({ publication_dir: "anicca-ios", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp4", native_owner: "anicca.jp4", integration_id: "cmn8x8hdv028uqx0y4gdfse5t", format_id: "reelclaw-card", form: "nudge-card" }),
  Object.freeze({ publication_dir: "anicca-ios", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp", native_owner: "anicca.jp", integration_id: "cmp9sdev5012voh0y58qs45xc", format_id: "reelclaw-card", form: "nudge-card" }),
  Object.freeze({ publication_dir: "honne-ai", product_id: "honne-ai", locale: "en", account_id: "@honne_reveal", native_owner: "honne_reveal", integration_id: "cmoig11ew001zlv0yk6vqo1us", format_id: "reelclaw", form: "relationship-confession" }),
  Object.freeze({ publication_dir: "honne-ai", product_id: "honne-ai", locale: "ja", account_id: "@honnevideo", native_owner: "honnevideo", integration_id: "cmnit95mg015rrm0ye5vm8dhl", format_id: "reelclaw", form: "relationship-confession" }),
]);

function discoverTarget(dataDir, target) {
  const file = path.join(dataDir, "tenants/dais-local/marketing/video-publication", target.publication_dir, "distribution.jsonl");
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line)).filter((row) => {
    const match = /^https:\/\/www\.tiktok\.com\/@([^/]+)\/video\/(\d+)\/?$/.exec(String(row.public_url || ""));
    return row.platform === "tiktok" && row.status === "published" && row.provider_reconciled === true && row.format_id === target.format_id && row.form === target.form && row.locale === target.locale && match && `@${match[1]}` === target.account_id;
  }).map((row) => {
    const match = /\/video\/(\d+)/.exec(row.public_url); const captionPath = path.resolve(String(row.caption_path || ""));
    if (row.format_id !== target.format_id || row.form !== target.form || row.locale !== target.locale || !/^c[a-z0-9]+$/.test(String(row.provider_id || "")) || !fs.statSync(captionPath, { throwIfNoEntry: false })?.isFile() || !Number.isFinite(Date.parse(row.ts))) throw new Error(`${target.account_id} verified distribution row invalid`);
    const bytes = fs.readFileSync(captionPath); if (crypto.createHash("sha256").update(bytes).digest("hex") !== row.caption_sha256) throw new Error(`${target.account_id} caption object integrity mismatch`);
    return Object.freeze({ tenant_id: "dais-local", product_id: target.product_id, locale: target.locale, account_id: target.account_id, native_owner: target.native_owner, integration_id: target.integration_id,
      provider_post_id: row.provider_id, shortcode: match[1], video_id: match[1], public_url: row.public_url, caption: bytes.toString("utf8"), published_at: row.ts });
  });
}

function discoverJp4(dataDir) { return discoverTarget(dataDir, TARGETS[0]); }
function discoverTargets(dataDir) { return TARGETS.flatMap((target) => discoverTarget(dataDir, target)); }

function snapshotFile(dataDir, expected, window) { return path.join(dataDir, "tenants", expected.tenant_id, "marketing", "metrics", expected.native_owner, expected.shortcode, `${window}.combined.json`); }

function delayed(dataDir, expected, window, observedAt) {
  const unavailable = { status: "unavailable", value: null, reason: "source_delayed" };
  const post = Object.fromEntries(["views", "likes", "comments", "shares", "saves", "reach", "watch_time", "completion", "engagement"].map((key) => [key, { ...unavailable }]));
  const snapshot = { schema_version: 1, kind: "tiktok_combined_metric_snapshot", ...expected, window, observed_at: observedAt,
    caption_sha256: crypto.createHash("sha256").update(expected.caption).digest("hex"), sources: { tiktok_native: { status: "unavailable", reason: "source_delayed", identity_verified: true }, postiz_post: { status: "unavailable", reason: "source_delayed" }, postiz_account: { status: "unavailable", reason: "source_delayed" } }, post, account_metrics: { status: "unavailable", reason: "source_delayed" } };
  const file = snapshotFile(dataDir, expected, window); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) return { created: false, file, snapshot: JSON.parse(fs.readFileSync(file, "utf8")) };
  const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`; fs.writeFileSync(temporary, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600, flag: "wx" }); fs.renameSync(temporary, file); fs.chmodSync(file, 0o600);
  return { created: true, file, snapshot };
}

async function runDue(nowMs = Date.now(), env = process.env, provided = null) {
  const dataDir = resolveDataRoot(env); const results = []; const expecteds = provided || discoverTargets(dataDir);
  for (const expected of expecteds) {
    for (const [window, delay] of Object.entries(WINDOWS)) {
      const existingFile = snapshotFile(dataDir, expected, window);
      if (fs.existsSync(existingFile)) { const snapshot = JSON.parse(fs.readFileSync(existingFile, "utf8")); results.push({ video_id: expected.video_id, window, state: "complete", telegram: await sendMetricSnapshot({ created: true, file: existingFile, snapshot }, env, dataDir) }); continue; }
      const dueMs = Date.parse(expected.published_at) + delay;
      if (nowMs < dueMs) { results.push({ video_id: expected.video_id, window, state: "pending", due_at: new Date(dueMs).toISOString() }); continue; }
      if (nowMs > dueMs + GRACE_MS) { const snapshot = delayed(dataDir, expected, window, new Date(nowMs).toISOString()); results.push({ video_id: expected.video_id, window, state: "source_delayed", telegram: await sendMetricSnapshot(snapshot, env, dataDir) }); continue; }
      const input = { tenantId: expected.tenant_id, productId: expected.product_id, locale: expected.locale, account: expected.account_id, integrationId: expected.integration_id, providerPostId: expected.provider_post_id, videoId: expected.video_id, publicUrl: expected.public_url, caption: expected.caption, window, publishedAt: expected.published_at };
      const observation = await collectTikTokWindow(input, env, new Date(nowMs).toISOString()); results.push({ video_id: expected.video_id, window, state: "measured", telegram: await sendMetricSnapshot(observation, env, dataDir) });
    }
    const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(nowMs)).map(({ type, value }) => [type, value])); const reportDay = `${parts.year}-${parts.month}-${parts.day}`;
    if (Number(parts.hour) > 17 || (Number(parts.hour) === 17 && Number(parts.minute) >= 30)) { const digest = persistDailyDigest({ dataDir, reportDay, observedAt: new Date(nowMs).toISOString(), expected }); results.push({ video_id: expected.video_id, window: "daily", state: digest.created ? "reported" : "complete", telegram: await sendMetricSnapshot(digest, env, dataDir) }); }
    else results.push({ video_id: expected.video_id, window: "daily", state: "pending", due_at: `${reportDay}T17:30:00+09:00` });
  }
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(nowMs)).map(({ type, value }) => [type, value])); const reportDay = `${parts.year}-${parts.month}-${parts.day}`;
  if (Number(parts.hour) >= 22 && !provided) {
    for (const [productId, persist] of [["honne-ai", persistHonneDaily], ["anicca-ios", persistAniccaDaily]]) { const summary = persist(dataDir, reportDay, new Date(nowMs).toISOString()); results.push({ product_id: productId, window: "daily-product", state: summary.created ? "reported" : "complete", telegram: await sendSummary(summary, env, dataDir) }); }
  }
  return results;
}

if (require.main === module) runDue().then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { GRACE_MS, TARGETS, WINDOWS, delayed, discoverJp4, discoverTarget, discoverTargets, runDue, snapshotFile };
