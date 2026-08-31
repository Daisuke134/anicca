"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { proveCalendarGateUnavailable } = require("./connector-coverage-assembler.js");
const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");
const {
  createEventSourceCapabilities, executeEventSourceHandoff, planEventSourceHandoff,
} = require("./event-source-handoff.js");
const {
  calendarEligibleConnpassCandidates,
  calendarEligibleLumaCandidates,
  evaluateCalendarCandidateGate,
  evaluateConnpassCalendarCandidateGate,
  isVerifiedCalendarCandidateGate,
  mapWithConcurrency,
} = require("./calendar-candidate-gate.js");

const FIXTURE_CONNPASS_API_KEY = ["connpass", "test", "key", "0".repeat(16)].join("-");

test("candidate evaluation is bounded to four concurrent workers and preserves source order", async () => {
  let active = 0;
  let peak = 0;
  const result = await mapWithConcurrency([0, 1, 2, 3, 4, 5, 6], 4, async (value) => {
    active += 1;
    peak = Math.max(peak, active);
    await new Promise((resolve) => setTimeout(resolve, (7 - value) * 2));
    active -= 1;
    return value * 2;
  });
  assert.equal(peak, 4);
  assert.deepEqual(result, [0, 2, 4, 6, 8, 10, 12]);
});

async function dateInventory() {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => {
      round += 1;
      return round === 1 ? [
        { href: "https://luma.com/noon", title: "Noon", cardText: "Noon", timelineText: "Aug 5" },
        { href: "https://luma.com/overlap", title: "Overlap", cardText: "Overlap", timelineText: "Aug 5" },
      ] : [];
    },
    advance: async () => ({ atEnd: true, scrollHeight: 100 }), stableEndRounds: 1,
  });
  const detail = (slug, title, start, end, venue) => normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event", name: title, description: `${title} public description`,
      startDate: start, endDate: end,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: venue, address: `${venue}, Tokyo` },
    }],
    controls: ["Register"],
  });
  return buildLumaDateInventory({
    coverage, inventory,
    details: [
      detail("noon", "Noon", "2026-08-05T12:00:00+09:00", "2026-08-05T13:00:00+09:00", "Shibuya Hall"),
      detail("overlap", "Overlap", "2026-08-05T10:30:00+09:00", "2026-08-05T11:30:00+09:00", "Tokyo Hall"),
    ],
    now: "2026-08-02T01:00:00.000Z",
  });
}

async function busy(events) {
  return inspectGoogleCalendarBusyInventory({
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() { return events; },
    },
    timeMin: "2026-08-02T00:00:00+09:00",
    timeMax: "2026-08-23T00:00:00+09:00",
    timeZone: "Asia/Tokyo",
    now: "2026-08-02T01:00:00.000Z",
  });
}

const timed = (id, start, end, location = "Office") => ({
  CalendarID: "primary", id, status: "confirmed", location,
  start: { dateTime: start }, end: { dateTime: end },
});

test("a direct busy overlap blocks only the candidate it overlaps", async () => {
  const inventory = await dateInventory();
  const busyInventory = await busy([
    timed("morning", "2026-08-05T10:00:00+09:00", "2026-08-05T11:00:00+09:00"),
  ]);
  const result = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory,
    date: "2026-08-05",
  });
  assert.equal(result.status, "evaluated");
  assert.deepEqual(result.candidates.map((row) => [row.event_ref, row.eligible]), [
    ["luma-event://event/overlap", false],
    ["luma-event://event/noon", true],
  ]);
  const noon = result.candidates.find((row) => row.event_ref === "luma-event://event/noon");
  const overlap = result.candidates.find((row) => row.event_ref === "luma-event://event/overlap");
  assert.equal(noon.conflict_event_refs.length, 0);
  assert.equal(overlap.conflict_event_refs.length, 1);
  assert.equal(isVerifiedCalendarCandidateGate(result), true);
  assert.equal(isVerifiedCalendarCandidateGate(structuredClone(result)), false);
  assert.deepEqual(calendarEligibleLumaCandidates(inventory, result), [
    { event_ref: "luma-event://event/noon", canonical_url: "https://luma.com/noon" },
  ]);
  assert.throws(() => calendarEligibleLumaCandidates(
    inventory, structuredClone(result),
  ), /calendar candidate gate invalid/i);
});

test("all-day events block every candidate with exact opaque conflicts", async () => {
  const inventory = await dateInventory();
  const allDayBusy = await busy([{
    CalendarID: "primary", id: "all-day", status: "confirmed",
    start: { date: "2026-08-05" }, end: { date: "2026-08-06" },
  }]);
  const allDay = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory: allDayBusy,
    date: "2026-08-05",
  });
  assert.equal(allDay.candidates.every((row) => row.eligible === false), true);
  assert.equal(allDay.candidates.every((row) => row.conflict_event_refs.length === 1), true);
  const unavailable = proveCalendarGateUnavailable({
    dateInventory: inventory, busyInventory: allDayBusy,
    calendarGate: allDay, date: "2026-08-05",
  });
  assert.equal(unavailable.date, "2026-08-05");
  assert.equal(unavailable.evidence_refs.length, 1);
});

test("unavailable proof keeps a minimal exact blocker set when many events overlap", async () => {
  const inventory = await dateInventory();
  const busyInventory = await busy(Array.from({ length: 21 }, (_, index) => timed(
    `overlap-${String(index).padStart(2, "0")}`,
    "2026-08-05T09:00:00+09:00",
    "2026-08-05T14:00:00+09:00",
  )));
  const gate = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory,
    date: "2026-08-05",
  });
  assert.equal(gate.candidates.every((row) => row.conflict_event_refs.length === 21), true);

  const unavailable = proveCalendarGateUnavailable({
    dateInventory: inventory,
    busyInventory,
    calendarGate: gate,
    date: "2026-08-05",
  });
  assert.equal(unavailable.evidence_refs.length, 1);
  assert.equal(gate.candidates.every((row) => (
    row.conflict_event_refs.includes(unavailable.evidence_refs[0])
  )), true);
});

test("an empty calendar leaves every candidate eligible, and fake inventories fail closed", async () => {
  const inventory = await dateInventory();
  const busyInventory = await busy([]);
  const result = await evaluateCalendarCandidateGate({
    dateInventory: inventory, busyInventory, date: "2026-08-05",
  });
  assert.equal(result.status, "evaluated");
  assert.equal(result.candidates.every((row) => row.eligible === true), true);
  await assert.rejects(evaluateCalendarCandidateGate({
    dateInventory: structuredClone(inventory), busyInventory, date: "2026-08-05",
  }), /calendar candidate gate invalid/i);
  await assert.rejects(evaluateCalendarCandidateGate({
    dateInventory: inventory, busyInventory: structuredClone(busyInventory), date: "2026-08-05",
  }), /calendar candidate gate invalid/i);
});

test("verified Connpass candidates use the same direct conflict gate without Luma provenance", async () => {
  const lumaOutcome = await runLumaCandidateSequence({ candidates: [], attempt: async () => {} });
  const capabilities = createEventSourceCapabilities({ connpassApiKey: FIXTURE_CONNPASS_API_KEY });
  const plan = planEventSourceHandoff({ date: "2026-08-05", lumaOutcome, capabilities });
  const handoff = await executeEventSourceHandoff({
    plan,
    connpassClient: { async searchEvents() {
      return { results_returned: 1, results_available: 1, results_start: 1, events: [{
        id: 101, title: "Connpass Night", catch: "Public", description: "Public details",
        started_at: "2026-08-05T12:00:00+09:00", ended_at: "2026-08-05T13:00:00+09:00",
        place: "Shibuya Hall", address: "Shibuya Hall, Tokyo",
        group: { subdomain: "tokyo-builders" },
      }] };
    } },
  });
  const gate = await evaluateConnpassCalendarCandidateGate({
    handoff,
    busyInventory: await busy([timed(
      "before", "2026-08-05T11:30:00+09:00", "2026-08-05T12:30:00+09:00",
    )]),
  });

  assert.equal(gate.candidates[0].eligible, false);
  assert.equal(gate.candidates[0].conflict_event_refs.length, 1);
  assert.deepEqual(calendarEligibleConnpassCandidates(handoff, gate), []);
  await assert.rejects(evaluateConnpassCalendarCandidateGate({
    handoff: structuredClone(handoff), busyInventory: await busy([]),
  }), /calendar candidate gate invalid/i);
});
