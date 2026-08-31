#!/usr/bin/env node
"use strict";

const fs = require("node:fs");

const CHECKS = Object.freeze({
  calendar_accepts_canonical_event_url(source) {
    return /add_argument\(["']--event-url["']/.test(source);
  },
  calendar_rejects_one_shot_url(source) {
    return /\/join\/complete\//.test(source) && /non-canonical-event-url/.test(source);
  },
  calendar_description_starts_with_event_url(source) {
    return /\(event_url,\s*args\.evidence_reference\)/.test(source);
  },
  connpass_preserves_discovered_host(source) {
    return /canonical_urls\[eid\]\s*=\s*url/.test(source)
      && /url\s*=\s*canonical_urls(?:\.get\(eid\)|\[eid\])/.test(source);
  },
  connpass_avoids_root_domain_reconstruction(source) {
    return !/url\s*=\s*["']https:\/\/connpass\.com\/event\/%s\/["']\s*%\s*eid/.test(source);
  },
});

function auditLegacyEventUrlSources({ calendarSource = "", connpassSource = "" } = {}) {
  const sources = {
    calendar_accepts_canonical_event_url: calendarSource,
    calendar_rejects_one_shot_url: calendarSource,
    calendar_description_starts_with_event_url: calendarSource,
    connpass_preserves_discovered_host: connpassSource,
    connpass_avoids_root_domain_reconstruction: connpassSource,
  };
  const checks = Object.fromEntries(
    Object.entries(CHECKS).map(([name, check]) => [name, Boolean(check(sources[name]))]),
  );
  const failed = Object.entries(checks)
    .filter(([, passed]) => !passed)
    .map(([name]) => name);
  return { ok: failed.length === 0, checks, failed };
}

function option(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function main() {
  const calendarPath = option("--calendar-source");
  const connpassPath = option("--connpass-source");
  if (!calendarPath || !connpassPath) {
    process.stderr.write("--calendar-source and --connpass-source are required\n");
    process.exitCode = 2;
    return;
  }
  const result = auditLegacyEventUrlSources({
    calendarSource: fs.readFileSync(calendarPath, "utf8"),
    connpassSource: fs.readFileSync(connpassPath, "utf8"),
  });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  process.exitCode = result.ok ? 0 : 1;
}

if (require.main === module) main();

module.exports = {
  auditLegacyEventUrlSources,
};
