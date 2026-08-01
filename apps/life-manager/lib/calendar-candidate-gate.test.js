"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const {
  calendarEligibleLumaCandidates,
  evaluateCalendarCandidateGate,
  isVerifiedCalendarCandidateGate,
} = require("./calendar-candidate-gate.js");

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

test("a short appointment leaves later free time while a directly overlapping candidate advances", async () => {
  const inventory = await dateInventory();
  const busyInventory = await busy([
    timed("morning", "2026-08-05T10:00:00+09:00", "2026-08-05T11:00:00+09:00"),
  ]);
  const routeCalls = [];
  const result = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory,
    date: "2026-08-05",
    homeLocation: "Home",
    routeMinutes: async (input) => { routeCalls.push(input); return input.direction === "inbound" ? 30 : 20; },
  });
  assert.equal(result.status, "evaluated");
  assert.deepEqual(result.candidates.map((row) => [row.event_ref, row.eligible]), [
    ["luma-event://event/overlap", false],
    ["luma-event://event/noon", true],
  ]);
  const noon = result.candidates.find((row) => row.event_ref === "luma-event://event/noon");
  const overlap = result.candidates.find((row) => row.event_ref === "luma-event://event/overlap");
  assert.equal(noon.expanded_start_at, "2026-08-05T02:25:00.000Z");
  assert.equal(noon.expanded_end_at, "2026-08-05T04:25:00.000Z");
  assert.equal(noon.conflict_event_refs.length, 0);
  assert.equal(overlap.conflict_event_refs.length, 1);
  assert.equal(routeCalls.length, 2);
  assert.equal(routeCalls[0].from, "Office");
  assert.equal(routeCalls[0].to, "Shibuya Hall, Tokyo");
  assert.equal(routeCalls[1].from, "Shibuya Hall, Tokyo");
  assert.equal(routeCalls[1].to, "Home");
  assert.equal(isVerifiedCalendarCandidateGate(result), true);
  assert.equal(isVerifiedCalendarCandidateGate(structuredClone(result)), false);
  assert.doesNotMatch(JSON.stringify(result), /Office|Shibuya Hall|Home/);
  assert.deepEqual(calendarEligibleLumaCandidates(inventory, result), [
    { event_ref: "luma-event://event/noon", canonical_url: "https://luma.com/noon" },
  ]);
  assert.throws(() => calendarEligibleLumaCandidates(
    inventory, structuredClone(result),
  ), /calendar candidate gate invalid/i);
});

test("travel expansion and all-day events block candidates with exact opaque conflicts", async () => {
  const inventory = await dateInventory();
  const travelConflict = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory: await busy([
      timed("before", "2026-08-05T11:30:00+09:00", "2026-08-05T11:45:00+09:00"),
    ]),
    date: "2026-08-05", homeLocation: "Home",
    routeMinutes: async () => 30,
  });
  assert.equal(travelConflict.candidates[0].eligible, false);
  assert.equal(travelConflict.candidates[0].conflict_event_refs.length, 1);

  const allDay = await evaluateCalendarCandidateGate({
    dateInventory: inventory,
    busyInventory: await busy([{
      CalendarID: "primary", id: "all-day", status: "confirmed",
      start: { date: "2026-08-05" }, end: { date: "2026-08-06" },
    }]),
    date: "2026-08-05", homeLocation: "Home",
    routeMinutes: async () => { throw new Error("must not route a blocked candidate"); },
  });
  assert.equal(allDay.candidates.every((row) => row.eligible === false), true);
  assert.equal(allDay.candidates.every((row) => row.conflict_event_refs.length === 1), true);
});

test("route failure requests recovery and fake inventories fail closed", async () => {
  const inventory = await dateInventory();
  const busyInventory = await busy([]);
  const result = await evaluateCalendarCandidateGate({
    dateInventory: inventory, busyInventory, date: "2026-08-05", homeLocation: "Home",
    routeMinutes: async () => null,
  });
  assert.equal(result.status, "recovery_required");
  assert.equal(result.reason, "route_unavailable");
  assert.equal(result.failed_event_ref, "luma-event://event/overlap");
  assert.equal(result.candidates.length, 0);
  await assert.rejects(evaluateCalendarCandidateGate({
    dateInventory: structuredClone(inventory), busyInventory, date: "2026-08-05",
    homeLocation: "Home", routeMinutes: async () => 10,
  }), /calendar candidate gate invalid/i);
  await assert.rejects(evaluateCalendarCandidateGate({
    dateInventory: inventory, busyInventory: structuredClone(busyInventory), date: "2026-08-05",
    homeLocation: "Home", routeMinutes: async () => 10,
  }), /calendar candidate gate invalid/i);
});
