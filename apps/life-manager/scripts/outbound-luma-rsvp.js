#!/usr/bin/env node
// scripts/outbound-luma-rsvp.js — register for ONE named Luma event, on purpose.
//
// The daily pass (scripts/outbound-pass.js) does not register while `auto_rsvp` is false, because
// the model's QUALIFY judgment is not built yet (TODO #10). This is the deliberate door: an
// operator (or an agent acting as QUALIFY) names the event and the ticket, and the SAME provider
// code path that the daily pass will use does the work.
//
// It never invents a verdict. After the RSVP it re-reads the screenshot off disk, performs a real
// HEAD on the canonical URL, and hands the bundle to runtime/loop/outbound/evidence.mjs.
//
// The browser is the SHARED CloakBrowser daily-driver. This script refuses to guess a port: the
// CDP URL must arrive in LM_BROWSER_CDP_URL, which is what `browser-guard.sh acquire` prints.
//
//   CDP=$(~/.config/ai/bin/browser-guard.sh acquire interactive:dais) \
//   LM_BROWSER_CDP_URL="$CDP" LM_OUTBOUND_NAME=… LM_OUTBOUND_EMAIL=… \
//     node scripts/outbound-luma-rsvp.js --slug <slug> --ticket "<ticket name>" --live
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const luma = require("../lib/providers/luma.js");
const { readIdentity, nameFor, artifactDir } = require("../lib/outbound-events-stages.js");

const ENGINE_DIR = path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound");
const loadEvidence = () => import(pathToFileURL(path.join(ENGINE_DIR, "evidence.mjs")).href);

function parseArgs(argv) {
  const args = argv.slice(2);
  const flag = (name, fallback = null) => {
    const index = args.indexOf(`--${name}`);
    return index >= 0 && args[index + 1] && !args[index + 1].startsWith("--") ? args[index + 1] : fallback;
  };
  return {
    slug: flag("slug"),
    ticket: flag("ticket"),
    live: args.includes("--live"),
  };
}

async function main(argv) {
  const args = parseArgs(argv);
  if (!args.slug) {
    process.stderr.write("usage: outbound-luma-rsvp.js --slug <slug> [--ticket \"<name>\"] [--live]\n");
    return 64;
  }

  const canonicalUrl = luma.canonicalEventUrl(args.slug);
  const event = await luma.fetchEventPage(args.slug);
  const screen = luma.screenEvent(event, args.ticket ? { ticketName: args.ticket } : {});

  const preview = {
    canonicalUrl,
    name: event.name,
    starts_at: event.startsAt,
    timezone: event.timezone,
    location_type: event.locationType,
    region: event.region,
    city: event.city,
    availability: event.availability,
    categories: event.categories,
    tickets: event.ticketTypes.map((t) => ({ name: t.name, type: t.type, cents: t.cents, approval: t.requireApproval })),
    screen: { ok: screen.ok, rejections: screen.rejections, ticket: screen.ticket && screen.ticket.name },
  };

  if (!screen.ok) {
    process.stdout.write(`${JSON.stringify({ mode: "refused", ...preview }, null, 2)}\n`);
    return 3;
  }
  if (!args.live) {
    process.stdout.write(`${JSON.stringify({ mode: "dry", ...preview }, null, 2)}\n`);
    return 0;
  }

  const identity = readIdentity(process.env);
  const receipt = await luma.rsvp(canonicalUrl, { ...identity, name: nameFor(event, identity) }, {
    cdpUrl: String(process.env.LM_BROWSER_CDP_URL || ""),
    artifactDir: artifactDir(process.env),
    ...(screen.ticket ? { ticketName: screen.ticket.name } : {}),
  });

  const { verifyEvidence } = await loadEvidence();
  let artifactBytes = null;
  try {
    artifactBytes = fs.readFileSync(receipt.artifactPath);
  } catch {
    artifactBytes = null;
  }
  let head = null;
  try {
    head = await luma.headStatus(receipt.canonicalUrl);
  } catch {
    head = null;
  }
  const bundle = luma.buildEvidence(receipt, {
    ...(artifactBytes ? { artifactBytes } : {}),
    headStatus: head,
  });
  const verdict = verifyEvidence(bundle);

  process.stdout.write(`${JSON.stringify({
    mode: "live",
    ...preview,
    receipt: {
      canonicalUrl: receipt.canonicalUrl,
      artifactPath: receipt.artifactPath,
      artifactBytes: artifactBytes ? artifactBytes.length : 0,
      guestKey: receipt.guestKey,
      venue: receipt.venue,
      startsAt: receipt.startsAt,
      httpEvidence: receipt.httpEvidence,
      observed: receipt.observed,
    },
    head_status: head,
    verdict: { ok: verdict.ok, failures: verdict.failures },
  }, null, 2)}\n`);

  return verdict.ok ? 0 : 1;
}

if (require.main === module) {
  main(process.argv)
    .then((code) => { process.exitCode = code; })
    .catch((error) => {
      process.stderr.write(`outbound-luma-rsvp failed: ${error && error.stack ? error.stack : error}\n`);
      process.exitCode = 2;
    });
}

module.exports = { main, parseArgs };
