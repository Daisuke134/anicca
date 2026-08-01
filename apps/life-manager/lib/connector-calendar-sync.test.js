"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { evaluateCalendarCandidateGate } = require("./calendar-candidate-gate.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const { buildVerifiedOutboundReceipt } = require("./outbound-success.js");
const {
  isVerifiedConnectorCalendarSync,
  syncVerifiedRegistrationToGoogleCalendar,
} = require("./connector-calendar-sync.js");

const TENANT = "dais-local";
const JOB_ID = `outbound-event:${"b".repeat(64)}`;
const ATTEMPT = 1;
const JOB = Object.freeze({ tenant_id: TENANT, job_id: JOB_ID, attempt: ATTEMPT });

async function registrationReceipt() {
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const hash = createHash("sha256").update(bytes).digest("hex");
  const evidence = await verifyOutboundEvidence({
    tenantId: TENANT,
    attemptRef: `runtime-attempt://${TENANT}/${JOB_ID}/${ATTEMPT}`,
    externalReceiptRef: "provider-receipt://luma/fixture-registration",
    artifactRef: `object://sha256/${hash}`,
    canonicalUrl: "https://luma.com/founder-night",
  }, {
    readExternalReceipt: async () => ({ kind: "provider_response", provider_id: "fixture", observed_at: "2026-08-02T01:00:00.000Z" }),
    readArtifact: async () => bytes,
    fetchImpl: async () => ({ status: 200 }),
  });
  return buildVerifiedOutboundReceipt({
    tenantId: TENANT, jobId: JOB_ID, attempt: ATTEMPT, verifiedAt: "2026-08-02T01:00:01.000Z",
  }, evidence);
}

async function inventoryAndGate() {
  const coverage = buildRollingEventCoverage({
    tenantId: TENANT, timeZone: "Asia/Tokyo", now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [{
      href: "https://luma.com/founder-night", title: "Founder Night", cardText: "Founder Night", timelineText: "Aug 5",
    }] : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }), stableEndRounds: 1,
  });
  const detail = normalizeLumaEventDetail({
    canonicalUrl: "https://luma.com/founder-night",
    jsonLd: [{
      "@type": "Event", name: "Founder Night", description: "Public founder event",
      startDate: "2026-08-05T12:00:00+09:00", endDate: "2026-08-05T13:00:00+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
    }], controls: ["Register"],
  });
  const dateInventory = buildLumaDateInventory({
    coverage, inventory, details: [detail], now: "2026-08-02T01:00:00.000Z",
  });
  const busyInventory = await inspectGoogleCalendarBusyInventory({
    calendar: { async listCalendarsRaw() { return [{ id: "primary" }]; }, async listAllEventsRaw() { return []; } },
    timeMin: "2026-08-02T00:00:00+09:00", timeMax: "2026-08-23T00:00:00+09:00",
    timeZone: "Asia/Tokyo", now: "2026-08-02T01:00:00.000Z",
  });
  const gate = await evaluateCalendarCandidateGate({
    dateInventory, busyInventory, date: "2026-08-05", homeLocation: "Home", routeMinutes: async () => 20,
  });
  return { dateInventory, gate };
}

test("verified Luma registration creates one idempotent Google Calendar event and returns only opaque refs", async () => {
  const { dateInventory, gate } = await inventoryAndGate();
  const receipt = await registrationReceipt();
  const created = [];
  let existing = [];
  const calendar = {
    async findConnectorEvents(input) { assert.match(input.idempotencyValue, /^[0-9a-f]{64}$/); return existing; },
    async createConnectorEvent(input) {
      created.push(input);
      const value = { id: "google-event-private-id", htmlLink: "https://calendar.google.com/calendar/event?eid=opaque" };
      existing = [value];
      return value;
    },
  };
  const input = {
    calendar, calendarId: "primary", dateInventory, calendarGate: gate,
    eventRef: "luma-event://event/founder-night", registrationReceipt: receipt, registrationJob: JOB,
  };
  const first = await syncVerifiedRegistrationToGoogleCalendar(input);
  const second = await syncVerifiedRegistrationToGoogleCalendar(input);
  assert.equal(first.status, "created");
  assert.equal(second.status, "existing");
  assert.equal(first.calendar_event_ref, second.calendar_event_ref);
  assert.equal(first.calendar_event_url, "https://calendar.google.com/calendar/event?eid=opaque");
  assert.equal(created.length, 1);
  assert.equal(created[0].canonicalUrl, "https://luma.com/founder-night");
  assert.equal(isVerifiedConnectorCalendarSync(first), true);
  assert.equal(isVerifiedConnectorCalendarSync(structuredClone(first)), false);
  assert.doesNotMatch(JSON.stringify(first), /google-event-private-id|primary/);
});

test("unverified receipts, ineligible candidates, and ambiguous existing events fail before create", async () => {
  const { dateInventory, gate } = await inventoryAndGate();
  const receipt = await registrationReceipt();
  let creates = 0;
  const calendar = {
    async findConnectorEvents() { return []; },
    async createConnectorEvent() { creates += 1; return {}; },
  };
  await assert.rejects(syncVerifiedRegistrationToGoogleCalendar({
    calendar, calendarId: "primary", dateInventory, calendarGate: gate,
    eventRef: "luma-event://event/founder-night", registrationReceipt: structuredClone(receipt), registrationJob: JOB,
  }), /connector calendar sync invalid/i);
  const blockedGate = await evaluateCalendarCandidateGate({
    dateInventory,
    busyInventory: await inspectGoogleCalendarBusyInventory({
      calendar: { async listCalendarsRaw() { return [{ id: "primary" }]; }, async listAllEventsRaw() { return [{ CalendarID: "primary", id: "busy", status: "confirmed", start: { date: "2026-08-05" }, end: { date: "2026-08-06" } }]; } },
      timeMin: "2026-08-02T00:00:00+09:00", timeMax: "2026-08-23T00:00:00+09:00", timeZone: "Asia/Tokyo", now: "2026-08-02T01:00:00.000Z",
    }),
    date: "2026-08-05", homeLocation: "Home", routeMinutes: async () => 20,
  });
  await assert.rejects(syncVerifiedRegistrationToGoogleCalendar({
    calendar, calendarId: "primary", dateInventory, calendarGate: blockedGate,
    eventRef: "luma-event://event/founder-night", registrationReceipt: receipt, registrationJob: JOB,
  }), /connector calendar sync invalid/i);
  assert.equal(creates, 0);
  const ambiguous = { ...calendar, async findConnectorEvents() { return [{ id: "a", htmlLink: "https://calendar.google.com/calendar/event?eid=a" }, { id: "b", htmlLink: "https://calendar.google.com/calendar/event?eid=b" }]; } };
  await assert.rejects(syncVerifiedRegistrationToGoogleCalendar({
    calendar: ambiguous, calendarId: "primary", dateInventory, calendarGate: gate,
    eventRef: "luma-event://event/founder-night", registrationReceipt: receipt, registrationJob: JOB,
  }), /connector calendar sync unavailable/i);
});
