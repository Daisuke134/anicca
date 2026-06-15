#!/usr/bin/env node
// ~/anicca/skills/life/call/call.js — B-call skill entrypoint (spec27 WF-B B-call).
//
// Anicca phones the user (Dais, +818046270314) ~15 min before each calendar event and
// talks two-way via Gemini Live (voice = Charon, male) bridged over the carrier's Media
// Streaming. The hard, bug-prone parts (μ-law↔PCM transcode + exact wire shapes) live in
// the products repo as pure, tested logic; this skill wires them to a carrier + Gemini.
//
// Provider-agnostic: the SAME Charon/Gemini bridge serves Twilio AND Telnyx. Telnyx is the
// default for +81 because Twilio fraud-control (error 21216) permanently blocks
// +818046270314 (JP geo-permissions are fully enabled — the block is account+destination
// fraud control that lifts only via an async Support ticket). Telnyx's outbound profile
// "anicca-out" has JP whitelisted and can legally dial +81.
// Design: docs/superpowers/specs/2026-06-16-life-call-telnyx-charon-design.md (products repo).
//
// Pure logic source of truth (products repo, node:test-covered):
//   apps/landing/netlify/functions/_lib/call-logic.js
//     buildGeminiSetup / buildGeminiAudioInput / parseGeminiAudio  (Gemini Live, Charon)
//     twilioMuLawToGeminiPcm16 / geminiPcm24ToTwilioMuLaw          (G.711 ↔ PCM16/24)
//     buildTwilioMediaFrame / buildConnectStreamTwiml              (Twilio path)
//     buildTelnyxMediaFrame / parseTelnyxStart / telnyxDialBody    (Telnyx path)
//
// Executable runners (products repo) that place the REAL call + record it:
//   apps/landing/scripts/call-bridge.cjs       --provider twilio|telnyx
//   apps/landing/scripts/life-call.mjs         (Twilio)
//   apps/landing/scripts/life-call-telnyx.mjs  (Telnyx — the +81 path to Dais)
//
// Usage:
//   node ~/anicca/skills/life/call.js                       place the real Charon call to Dais (Telnyx)
//   node ~/anicca/skills/life/call.js --provider twilio     use the Twilio carrier instead
//   node ~/anicca/skills/life/call.js --to +E164            override the destination
//   node ~/anicca/skills/life/call.js --dry-run             build the dial payload only, no side effects

"use strict";

const path = require("path");
const { spawnSync } = require("child_process");

// Resolve the products-repo working tree from env (ANICCA_PRODUCTS) or the conventional
// sibling checkout. This skill body stays tiny; the heavy, tested code lives in products.
function productsRoot() {
  const env = process.env.ANICCA_PRODUCTS;
  if (env) return env;
  const home = process.env.HOME || require("os").homedir();
  return path.join(home, "anicca-project");
}

/** Map a provider name to its products-repo runner script. */
function runnerFor(provider) {
  const root = productsRoot();
  const scripts = path.join(root, "apps", "landing", "scripts");
  return String(provider).toLowerCase() === "twilio"
    ? path.join(scripts, "life-call.mjs")
    : path.join(scripts, "life-call-telnyx.mjs"); // default: Telnyx (+81 / Dais)
}

/**
 * Place the real Charon call by delegating to the products-repo runner.
 * @param {object} [opts]
 * @param {string} [opts.provider="telnyx"] - "telnyx" | "twilio"
 * @param {string} [opts.to] - E.164 destination (default = the runner's Dais number)
 * @param {boolean} [opts.dryRun=false]
 * @returns {number} the runner's exit code
 */
function placeCall(opts = {}) {
  const provider = opts.provider || process.env.LIFE_CALL_PROVIDER || "telnyx";
  const runner = runnerFor(provider);
  const args = [runner];
  if (opts.to) args.push(`--to=${opts.to}`);
  if (opts.dryRun) args.push("--dry-run");
  const r = spawnSync("node", args, { stdio: "inherit", env: process.env });
  return r.status == null ? 1 : r.status;
}

module.exports = { placeCall, runnerFor, productsRoot };

// CLI: parse --provider/--to/--dry-run and place the call.
if (require.main === module) {
  const argv = process.argv.slice(2);
  const opts = { dryRun: argv.includes("--dry-run") };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--provider") opts.provider = argv[++i];
    else if (argv[i].startsWith("--provider=")) opts.provider = argv[i].split("=")[1];
    else if (argv[i] === "--to") opts.to = argv[++i];
    else if (argv[i].startsWith("--to=")) opts.to = argv[i].split("=")[1];
  }
  process.exit(placeCall(opts));
}
