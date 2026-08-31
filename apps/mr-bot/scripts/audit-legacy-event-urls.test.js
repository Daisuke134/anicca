"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  auditLegacyEventUrlSources,
} = require("./audit-legacy-event-urls.js");

const SAFE_CALENDAR = `
parser.add_argument("--event-url", default="")
ONE_SHOT_URL_MARKER = "/join/complete/"
if event_url and ONE_SHOT_URL_MARKER in event_url: refuse("non-canonical-event-url")
description = "\\n\\n".join(p for p in (event_url, args.evidence_reference) if p)
`;

const SAFE_CONNPASS = `
canonical_urls[eid] = url
url = canonical_urls[eid]
`;

test("safe deployed sources pass every canonical URL regression check", () => {
  const result = auditLegacyEventUrlSources({
    calendarSource: SAFE_CALENDAR,
    connpassSource: SAFE_CONNPASS,
  });

  assert.equal(result.ok, true);
  assert.deepEqual(result.failed, []);
});

test("root-domain reconstruction and evidence-only calendar links fail closed", () => {
  const result = auditLegacyEventUrlSources({
    calendarSource: "description = args.evidence_reference",
    connpassSource: 'url = "https://connpass.com/event/%s/" % eid',
  });

  assert.equal(result.ok, false);
  assert.deepEqual(result.failed, [
    "calendar_accepts_canonical_event_url",
    "calendar_rejects_one_shot_url",
    "calendar_description_starts_with_event_url",
    "connpass_preserves_discovered_host",
    "connpass_avoids_root_domain_reconstruction",
  ]);
});
