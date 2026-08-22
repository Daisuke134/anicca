#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const { EXPECTED, collectWindow, persistDelayedSnapshot, sendMetricSnapshot } = require("./instagram-metrics-read.js");

const WINDOWS = Object.freeze({ "2h": 2 * 3600_000, "24h": 24 * 3600_000, "72h": 72 * 3600_000, "7d": 7 * 86400_000 });
const GRACE_MS = 90 * 60_000;

function snapshotFile(dataDir, window) {
  return path.join(dataDir, "tenants", EXPECTED.tenant_id, "marketing", "metrics", EXPECTED.native_owner, EXPECTED.shortcode, `${window}.combined.json`);
}

async function runDue(nowMs = Date.now(), env = process.env) {
  const dataDir = resolveDataRoot(env); const publishedMs = Date.parse(EXPECTED.published_at); const results = [];
  if (!Number.isFinite(nowMs)) throw new Error("Instagram metrics due clock invalid");
  for (const [window, delay] of Object.entries(WINDOWS)) {
    if (fs.existsSync(snapshotFile(dataDir, window))) { results.push({ window, state: "complete" }); continue; }
    const dueMs = publishedMs + delay;
    if (nowMs < dueMs) { results.push({ window, state: "pending", due_at: new Date(dueMs).toISOString() }); continue; }
    if (nowMs > dueMs + GRACE_MS) {
      const snapshot = persistDelayedSnapshot({ dataDir, window, observedAt: new Date(nowMs).toISOString() });
      const telegram = await sendMetricSnapshot(snapshot, env, dataDir);
      results.push({ window, state: "source_delayed", telegram }); continue;
    }
    const observation = await collectWindow(window, env, new Date(nowMs).toISOString());
    results.push({ window, state: "measured", telegram: observation.telegram });
  }
  return results;
}

if (require.main === module) runDue().then((result) => process.stdout.write(`${JSON.stringify(result)}\n`)).catch((error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
module.exports = { GRACE_MS, WINDOWS, runDue, snapshotFile };
