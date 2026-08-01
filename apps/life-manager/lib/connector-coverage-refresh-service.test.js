"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { evaluateCalendarCandidateGate } = require("./calendar-candidate-gate.js");
const { syncVerifiedRegistrationToGoogleCalendar } = require("./connector-calendar-sync.js");
const {
  buildVerifiedRegistrationCoverageEvidence,
  proveAllDayCalendarUnavailable,
  rebuildRollingEventCoverage,
} = require("./connector-coverage-assembler.js");
const {
  createConnectorCoverageRefreshService,
} = require("./connector-coverage-refresh-service.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { buildEventApplicationJob } = require("./outbound-event-job.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const { buildVerifiedOutboundReceipt } = require("./outbound-success.js");
const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");

const TENANT = "dais-local";
const NOW = "2026-08-02T01:00:00.000Z";

function currentCoverage() {
  return buildRollingEventCoverage({
    tenantId: TENANT,
    timeZone: "Asia/Tokyo",
    now: NOW,
    resolvedDays: [],
  });
}

async function dateInventory(coverage, slug = "founder-night") {
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [{
      href: `https://luma.com/${slug}`,
      title: "Founder Night",
      cardText: "Founder Night",
      timelineText: "Aug 5",
    }] : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
  const detail = normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event",
      name: "Founder Night",
      description: "Public founder gathering",
      startDate: "2026-08-05T12:00:00+09:00",
      endDate: "2026-08-05T13:00:00+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
    }],
    controls: ["Register"],
  });
  return buildLumaDateInventory({ coverage, inventory, details: [detail], now: NOW });
}

async function completedRegistration(slug = "founder-night") {
  const job = buildEventApplicationJob({
    tenantId: TENANT,
    eventUrl: `https://luma.com/${slug}`,
    eventStartIso: "2026-08-05T12:00:00+09:00",
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });
  const claimedJob = Object.freeze({ ...job, attempt: 1 });
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const hash = createHash("sha256").update(bytes).digest("hex");
  const evidence = await verifyOutboundEvidence({
    tenantId: TENANT,
    attemptRef: `runtime-attempt://${TENANT}/${job.job_id}/1`,
    externalReceiptRef: "provider-receipt://luma/fixture-registration",
    artifactRef: `object://sha256/${hash}`,
    canonicalUrl: `https://luma.com/${slug}`,
  }, {
    async readExternalReceipt() {
      return { kind: "provider_response", provider_id: "fixture", observed_at: NOW };
    },
    async readArtifact() { return bytes; },
    async fetchImpl() { return { status: 200 }; },
  });
  return Object.freeze({
    event_ref: job.input_refs.event_ref,
    job: claimedJob,
    receipt: buildVerifiedOutboundReceipt({
      tenantId: TENANT,
      jobId: job.job_id,
      attempt: 1,
      verifiedAt: NOW,
    }, evidence),
  });
}

async function busyInventory() {
  return inspectGoogleCalendarBusyInventory({
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() {
        return [{
          CalendarID: "primary",
          id: "fixed-all-day",
          status: "confirmed",
          start: { date: "2026-08-06" },
          end: { date: "2026-08-07" },
        }];
      },
    },
    timeMin: "2026-08-01T15:00:00.000Z",
    timeMax: "2026-08-22T15:00:00.000Z",
    timeZone: "Asia/Tokyo",
    now: NOW,
  });
}

function makeService(input) {
  return createConnectorCoverageRefreshService({
    receiptReader: input.receiptReader,
    calendar: input.calendar,
    calendarId: "primary",
    homeLocation: "Tokyo",
    routeMinutes: input.routeMinutes || (async () => 20),
    now: () => NOW,
    readDateInventory: input.readDateInventory,
    readBusyCalendar: async () => busyInventory(),
    gateDateCalendar: evaluateCalendarCandidateGate,
    syncRegistrationCalendar: syncVerifiedRegistrationToGoogleCalendar,
    buildRegistrationCoverageEvidence: buildVerifiedRegistrationCoverageEvidence,
    proveUnavailableDay: proveAllDayCalendarUnavailable,
    rebuildCoverage: rebuildRollingEventCoverage,
  });
}

test("verified RSVP becomes a Calendar event and coverage while a real all-day blocker closes only its date", async () => {
  const coverage = currentCoverage();
  const inventory = await dateInventory(coverage);
  const registration = await completedRegistration();
  const created = [];
  const refresh = makeService({
    receiptReader: { async listForCoverage() { return [registration]; } },
    readDateInventory: async () => inventory,
    calendar: {
      async findConnectorEvents() { return []; },
      async createConnectorEvent(input) {
        created.push(input);
        return { id: "created-event", htmlLink: "https://calendar.google.com/calendar/event?eid=created" };
      },
    },
  });

  const result = await refresh({
    coverage,
    tenantId: TENANT,
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  });

  assert.equal(created.length, 1);
  assert.equal(created[0].canonicalUrl, "https://luma.com/founder-night");
  assert.equal(result.coverage.counts.covered_new, 1);
  assert.equal(result.coverage.counts.unavailable, 1);
  assert.equal(result.coverage.counts.open, 19);
  assert.deepEqual(result.observedOutcomes, [{ date: "2026-08-05", observed_status: "booked" }]);
});

test("an existing exact Calendar registration rebuilds coverage without calling travel routing", async () => {
  const coverage = currentCoverage();
  const inventory = await dateInventory(coverage);
  const registration = await completedRegistration();
  let routeCalls = 0;
  let creates = 0;
  const refresh = makeService({
    receiptReader: { async listForCoverage() { return [registration]; } },
    readDateInventory: async () => inventory,
    routeMinutes: async () => { routeCalls += 1; throw new Error("route unavailable"); },
    calendar: {
      async findConnectorEvents() {
        return [{
          id: "existing-event",
          htmlLink: "https://calendar.google.com/calendar/event?eid=existing",
        }];
      },
      async createConnectorEvent() { creates += 1; },
    },
  });

  const result = await refresh({ coverage, tenantId: TENANT });
  assert.equal(result.coverage.counts.covered_existing, 1);
  assert.equal(result.coverage.counts.unavailable, 1);
  assert.equal(result.coverage.counts.open, 19);
  assert.equal(routeCalls, 0);
  assert.equal(creates, 0);
});

test("a completed receipt absent from the fresh exhaustive inventory cannot create Calendar or coverage", async () => {
  const coverage = currentCoverage();
  const registration = await completedRegistration("not-in-inventory");
  let creates = 0;
  const refresh = makeService({
    receiptReader: { async listForCoverage() { return [registration]; } },
    readDateInventory: async () => dateInventory(coverage),
    calendar: {
      async findConnectorEvents() { return []; },
      async createConnectorEvent() { creates += 1; },
    },
  });

  await assert.rejects(refresh({
    coverage,
    tenantId: TENANT,
    identityRef: "identity://dais-local/luma",
    browserProfileRef: "browser-profile://cloakbrowser/daily-driver",
    calendarRef: "calendar://google/primary",
  }), /coverage refresh unavailable/i);
  assert.equal(creates, 0);
});
