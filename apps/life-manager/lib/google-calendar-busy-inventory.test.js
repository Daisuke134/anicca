"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  inspectGoogleCalendarBusyInventory,
  isVerifiedGoogleCalendarBusyInventory,
} = require("./google-calendar-busy-inventory.js");

const WINDOW = Object.freeze({
  timeMin: "2026-08-02T00:00:00+09:00",
  timeMax: "2026-08-23T00:00:00+09:00",
  timeZone: "Asia/Tokyo",
  now: "2026-08-02T01:00:00.000Z",
});

function transport(overrides = {}) {
  return {
    async listCalendarsRaw() {
      return [{ id: "primary" }, { id: "work" }, { id: "school" }];
    },
    async listAllEventsRaw() {
      return [
        {
          CalendarID: "work", id: "meeting-1", status: "confirmed", summary: "Private meeting",
          location: "Private office", start: { dateTime: "2026-08-05T09:00:00+09:00" },
          end: { dateTime: "2026-08-05T10:00:00+09:00" },
        },
        {
          CalendarID: "school", id: "all-day-1", status: "confirmed", summary: "Private all day",
          start: { date: "2026-08-06" }, end: { date: "2026-08-07" },
        },
        {
          CalendarID: "primary", id: "free-1", status: "confirmed", transparency: "transparent",
          start: { dateTime: "2026-08-05T11:00:00+09:00" }, end: { dateTime: "2026-08-05T12:00:00+09:00" },
        },
        {
          CalendarID: "primary", id: "cancelled-1", status: "cancelled",
          start: { dateTime: "2026-08-05T13:00:00+09:00" }, end: { dateTime: "2026-08-05T14:00:00+09:00" },
        },
      ];
    },
    ...overrides,
  };
}

test("reads every calendar and emits reference-only timed and all-day busy intervals", async () => {
  const calls = [];
  const base = transport();
  const result = await inspectGoogleCalendarBusyInventory({
    ...WINDOW,
    calendar: {
      async listCalendarsRaw(options) { calls.push(["calendars", options]); return base.listCalendarsRaw(); },
      async listAllEventsRaw(uid, options) { calls.push(["events", uid, options]); return base.listAllEventsRaw(); },
    },
  });
  assert.equal(result.calendar_count, 3);
  assert.equal(result.source_event_count, 4);
  assert.equal(result.busy_event_count, 2);
  assert.equal(result.excluded_event_count, 2);
  assert.equal(result.busy_intervals[0].kind, "timed");
  assert.equal(result.busy_intervals[0].start_at, "2026-08-05T00:00:00.000Z");
  assert.equal(result.busy_intervals[0].end_at, "2026-08-05T01:00:00.000Z");
  assert.equal(result.busy_intervals[1].kind, "all_day");
  assert.equal(result.busy_intervals[1].start_date, "2026-08-06");
  assert.equal(result.busy_intervals[1].end_date, "2026-08-07");
  assert.match(result.busy_intervals[0].calendar_ref, /^calendar-evidence:\/\/google\/calendar\/[0-9a-f]{64}$/);
  assert.match(result.busy_intervals[0].event_ref, /^calendar-evidence:\/\/google\/event\/[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(result), /primary|work|school|meeting-1|Private meeting|Private office/);
  assert.equal(isVerifiedGoogleCalendarBusyInventory(result), true);
  assert.equal(isVerifiedGoogleCalendarBusyInventory(structuredClone(result)), false);
  assert.deepEqual(calls, [
    ["calendars", { strict: true }],
    ["events", "dais-local", {
      timeMin: WINDOW.timeMin, timeMax: WINDOW.timeMax, maxResults: 2500, strict: true,
    }],
  ]);
});

test("empty calendars are valid only when both exhaustive reads succeed", async () => {
  const result = await inspectGoogleCalendarBusyInventory({
    ...WINDOW,
    calendar: transport({
      async listCalendarsRaw() { return []; },
      async listAllEventsRaw() { return []; },
    }),
  });
  assert.equal(result.calendar_count, 0);
  assert.equal(result.source_event_count, 0);
  assert.equal(result.busy_event_count, 0);
});

test("unknown calendars, duplicate events, malformed intervals, and provider errors fail closed", async () => {
  const cases = [
    [{ CalendarID: "unknown", id: "e", status: "confirmed", start: { dateTime: "2026-08-05T09:00:00+09:00" }, end: { dateTime: "2026-08-05T10:00:00+09:00" } }],
    [
      { CalendarID: "work", id: "e", status: "confirmed", start: { dateTime: "2026-08-05T09:00:00+09:00" }, end: { dateTime: "2026-08-05T10:00:00+09:00" } },
      { CalendarID: "work", id: "e", status: "confirmed", start: { dateTime: "2026-08-05T11:00:00+09:00" }, end: { dateTime: "2026-08-05T12:00:00+09:00" } },
    ],
    [{ CalendarID: "work", id: "e", status: "confirmed", start: { dateTime: "bad" }, end: { dateTime: "also-bad" } }],
  ];
  for (const events of cases) await assert.rejects(inspectGoogleCalendarBusyInventory({
    ...WINDOW,
    calendar: transport({ async listAllEventsRaw() { return events; } }),
  }), /calendar busy inventory invalid/i);
  await assert.rejects(inspectGoogleCalendarBusyInventory({
    ...WINDOW,
    calendar: transport({ async listCalendarsRaw() { throw new Error("provider down"); } }),
  }), /calendar busy inventory unavailable/i);
});
