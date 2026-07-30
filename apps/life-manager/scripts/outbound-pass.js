#!/usr/bin/env node
// scripts/outbound-pass.js — the daily outbound pass entrypoint (07:30 JST, via launchd).
//
// Thin CLI over lib/outbound-runtime.js. It loads a pack config, resolves the pack's provider
// stages, and runs one pass.
//
// The `events` pack is wired to the real Luma provider (TODO #7): it discovers from Luma's public
// discover feed, hydrates each candidate's event page so freeness can be proven, screens for
// free / in-person / in-region / open, and — when the pack config turns `auto_rsvp` on — RSVPs
// through the leased CloakBrowser and puts the result through the evidence gate.
//
// `funders` and `jobs` are still unwired and say so. Their stages return a named refusal, so the
// pass produces an HONEST failure in the trace ledger and an honest failure line in Telegram
// rather than a fake success.
"use strict";

const { runOutboundPass } = require("../lib/outbound-runtime.js");
const { loadPackConfig, PACKS } = require("../lib/outbound-config.js");
const { buildStages: buildEventStages } = require("../lib/outbound-events-stages.js");

function stagesFor(pack, deps = {}) {
  const notWired = (stage) => async () => ({
    ok: false,
    reason: `${stage}_not_wired_for_${pack}`,
  });
  if (pack === "events") return buildEventStages(deps);
  return {
    discover: notWired("discover"),
    qualify: notWired("qualify"),
    act: notWired("act"),
    evidence: notWired("evidence"),
    track: notWired("track"),
    learn: notWired("learn"),
  };
}

async function main(argv) {
  const args = argv.slice(2);
  const index = args.indexOf("--pack");
  const requested = index >= 0 && args[index + 1] ? args[index + 1] : null;
  const packs = requested ? [requested] : PACKS;
  const passes = [];
  for (const pack of packs) {
    passes.push(await runOutboundPass({
      pack,
      config: loadPackConfig(pack),
      stages: stagesFor(pack),
      homeDir: process.env.HOME,
      nowMs: Date.now(),
      telegram: {
        token: process.env.LM_TELEGRAM_BOT_TOKEN,
        chatId: process.env.LM_TELEGRAM_CHAT_ID,
      },
    }));
  }
  process.stdout.write(`${JSON.stringify({ passes }, null, 2)}\n`);
  // Non-zero while nothing verifies, so launchd's "last exit code" and the guardian both see the
  // truth instead of a green tick over an engine with no providers.
  return passes.some((pass) => (pass.claimed || 0) > 0) ? 0 : 1;
}

if (require.main === module) {
  main(process.argv)
    .then((code) => { process.exitCode = code; })
    .catch((error) => {
      process.stderr.write(`outbound-pass failed: ${error && error.stack ? error.stack : error}\n`);
      process.exitCode = 2;
    });
}

module.exports = { main, stagesFor };
