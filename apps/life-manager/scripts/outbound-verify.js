#!/usr/bin/env node
// scripts/outbound-verify.js — the independent GREEN gate.
//
// The pass runtime writes "outcome": "verified" into the trace. That is a CLAIM, and a loop that
// grades its own homework is precisely the failure mode this engine exists to prevent (spec §2.1:
// a live loop whose success test was a DOM regex that matched the word "cancel" in the
// cancellation policy, and therefore reported success forever while doing nothing).
//
// So this verifier trusts NOTHING in the trace's own verdict. For every claimed row it:
//   1. re-reads the artifact file off disk (not the bytes the pass held in memory), and
//   2. re-runs the pure evidence gate over the recorded E1/E3 plus those freshly-read bytes.
// Only rows that survive that recheck count. Then, and only then, applyDay may award a green day.
//
// Rules: one increment per calendar day; a day with zero re-verified results resets green_days to
// 0; 7 consecutive green days = the pack is GREEN. Every completed pass touches the heartbeat file
// under the canonical data root (see streak.mjs), which the guardian watches once TODO #4 wires it.
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const { readTrace } = require("../lib/outbound-runtime.js");
const { PACKS } = require("../lib/outbound-config.js");

const ENGINE_DIR = path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound");
const engineUrl = (file) => pathToFileURL(path.join(ENGINE_DIR, file)).href;

function readArtifactBytes(artifactPath) {
  if (!artifactPath) return null;
  try {
    return fs.readFileSync(artifactPath);
  } catch {
    // A missing, unreadable or deleted artifact is not an error to report — it is simply the
    // absence of evidence, which the gate turns into E2_ABSENT.
    return null;
  }
}

/**
 * Independently re-check one claimed trace row.
 * @returns {Promise<{ok: boolean, failures: string[]}>}
 */
async function recheckEntry(entry, { verifyEvidence }) {
  const evidence = (entry && entry.evidence) || {};
  const e2 = evidence.e2 && typeof evidence.e2 === "object" ? evidence.e2 : null;
  const bytes = readArtifactBytes(e2 && e2.path);
  const verdict = verifyEvidence({
    e1: evidence.e1 || null,
    e2: bytes ? { ...e2, bytes } : (e2 ? { ...e2, bytes: undefined } : null),
    e3: evidence.e3 || null,
  });
  return { ok: verdict.ok, failures: verdict.failures.map((failure) => failure.code) };
}

async function verifyPass(request = {}) {
  const pack = String(request.pack || "");
  if (!PACKS.includes(pack)) {
    throw new Error(`outbound pack must be one of ${PACKS.join(", ")}, got ${JSON.stringify(pack)}`);
  }
  const homeDir = String(request.homeDir || process.env.HOME || "");
  if (!homeDir) throw new Error("outbound verify needs a home directory");
  const date = String(request.date || new Date().toISOString().slice(0, 10));

  const [{ verifyEvidence }, streak] = await Promise.all([
    import(engineUrl("evidence.mjs")),
    import(engineUrl("streak.mjs")),
  ]);

  const claims = readTrace(homeDir, pack)
    .filter((entry) => entry && entry.outcome === "verified")
    .filter((entry) => String(entry.ts || "").slice(0, 10) === date);

  const rejected = [];
  let verified = 0;
  for (const entry of claims) {
    const verdict = await recheckEntry(entry, { verifyEvidence });
    if (verdict.ok) verified += 1;
    else rejected.push({ target: entry.target, ts: entry.ts, failures: verdict.failures });
  }

  const statePath = streak.streakStatePath(homeDir);
  const next = streak.applyDay(streak.readStreak(statePath), { pack, date, verifiedCount: verified });
  streak.writeStreak(statePath, next);
  streak.touchHeartbeat(streak.heartbeatPath(homeDir));

  const packState = next[pack] || streak.emptyPackStreak();
  return {
    pack,
    date,
    claimed: claims.length,
    verified,
    rejected,
    green_days: packState.green_days,
    green: streak.isGreen(next, pack),
  };
}

async function main(argv) {
  const args = argv.slice(2);
  const flag = (name, fallback) => {
    const index = args.indexOf(`--${name}`);
    return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
  };
  const packs = flag("pack") ? [flag("pack")] : PACKS;
  const date = flag("date", new Date().toISOString().slice(0, 10));
  const results = [];
  for (const pack of packs) {
    results.push(await verifyPass({ pack, date, homeDir: process.env.HOME }));
  }
  process.stdout.write(`${JSON.stringify({ date, results }, null, 2)}\n`);
  // Exit non-zero when nothing at all could be re-verified: launchd and the guardian should see a
  // failing job rather than a silent one.
  return results.some((row) => row.verified > 0) ? 0 : 1;
}

if (require.main === module) {
  main(process.argv)
    .then((code) => { process.exitCode = code; })
    .catch((error) => {
      process.stderr.write(`outbound-verify failed: ${error && error.stack ? error.stack : error}\n`);
      process.exitCode = 2;
    });
}

module.exports = { verifyPass, recheckEntry, main };
