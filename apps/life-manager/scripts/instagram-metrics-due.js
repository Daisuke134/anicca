#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const { EXPECTED, collectWindow, persistDailyDigest, persistDelayedSnapshot, sendMetricSnapshot } = require("./instagram-metrics-read.js");

const WINDOWS = Object.freeze({ "2h": 2 * 3600_000, "24h": 24 * 3600_000, "72h": 72 * 3600_000, "7d": 7 * 86400_000 });
const GRACE_MS = 90 * 60_000;

function snapshotFile(dataDir, window, expected = EXPECTED) {
  return path.join(dataDir, "tenants", expected.tenant_id, "marketing", "metrics", expected.native_owner, expected.shortcode, `${window}.combined.json`);
}

function discoverExpected(dataDir) {
  const file = path.join(dataDir, "tenants", "dais-local", "marketing", "video-publication", "anicca-ios", "distribution.jsonl");
  if (!fs.existsSync(file)) return [];
  const rows = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
  const found = [];
  for (const row of rows) {
    if (row.platform !== "instagram" || row.status !== "published" || row.provider_reconciled !== true) continue;
    if (row.format_id !== "reelclaw-card" || row.form !== "nudge-card" || row.locale !== "ja") continue;
    const match = /^https:\/\/www\.instagram\.com\/reel\/([A-Za-z0-9_-]+)\/$/.exec(String(row.public_url || ""));
    const captionPath = path.resolve(String(row.caption_path || ""));
    if (!match || !/^c[a-z0-9]+$/.test(String(row.provider_id || "")) || !fs.statSync(captionPath, { throwIfNoEntry: false })?.isFile() || !Number.isFinite(Date.parse(row.ts))) throw new Error("Instagram verified distribution row invalid");
    const caption = fs.readFileSync(captionPath, "utf8");
    if (crypto.createHash("sha256").update(fs.readFileSync(captionPath)).digest("hex") !== row.caption_sha256) throw new Error("Instagram caption object integrity mismatch");
    found.push(Object.freeze({ tenant_id: "dais-local", product_id: "anicca-ios", locale: "ja", account_id: "@anicca.jp1", native_owner: "anicca.ios.jp",
      integration_id: "cmn8ycvtn02djqx0ytuisn9mw", provider_post_id: row.provider_id, shortcode: match[1], public_url: row.public_url, caption, published_at: row.ts }));
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
