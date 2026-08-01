"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { evaluateEventCalendarAvailability } = require("./event-calendar-availability.js");

const freebusy = {
  calendars: {
    "work@example.invalid": { busy: [{ start: "2026-08-10T01:00:00Z", end: "2026-08-10T02:00:00Z" }] },
    "personal@example.invalid": { busy: [{ start: "2026-08-10T03:00:00Z", end: "2026-08-10T04:00:00Z" }] },
  },
};

function candidate(slug, start, end, before = 30, after = 30) {
  return {
    event_ref: `luma-event://event/${slug}`,
    start_at: start,
    end_at: end,
    travel_before_minutes: before,
    travel_after_minutes: after,
  };
}

test("all calendars are unioned and both travel buffers participate in conflicts", () => {
  const result = evaluateEventCalendarAvailability({
    window_start: "2026-08-10T00:00:00Z",
    window_end: "2026-08-10T08:00:00Z",
    freebusy,
    candidates: [
      candidate("before-conflict", "2026-08-10T02:15:00Z", "2026-08-10T02:45:00Z"),
      candidate("after-conflict", "2026-08-10T02:15:00Z", "2026-08-10T02:45:00Z", 0, 30),
      candidate("free", "2026-08-10T05:00:00Z", "2026-08-10T06:00:00Z", 30, 45),
    ],
  });
  assert.equal(result.calendar_count, 2);
  assert.equal(result.busy_interval_count, 2);
  assert.deepEqual(result.eligible_event_refs, ["luma-event://event/free"]);
  assert.deepEqual(result.conflicts.map(({ event_ref }) => event_ref), [
    "luma-event://event/before-conflict",
    "luma-event://event/after-conflict",
  ]);
});

test("one calendar provider error fails closed instead of inventing free time", () => {
  assert.throws(() => evaluateEventCalendarAvailability({
    window_start: "2026-08-10T00:00:00Z",
    window_end: "2026-08-10T08:00:00Z",
    freebusy: { calendars: { a: { busy: [] }, b: { errors: [{ reason: "notFound" }] } } },
    candidates: [],
  }), /incomplete/i);
});

test("overlapping busy intervals merge and window overflow is not eligible", () => {
  const result = evaluateEventCalendarAvailability({
    window_start: "2026-08-10T00:00:00Z",
    window_end: "2026-08-10T08:00:00Z",
    freebusy: { calendars: {
      a: { busy: [{ start: "2026-08-10T01:00:00Z", end: "2026-08-10T03:00:00Z" }] },
      b: { busy: [{ start: "2026-08-10T02:00:00Z", end: "2026-08-10T04:00:00Z" }] },
    } },
    candidates: [candidate("window-overflow", "2026-08-10T07:30:00Z", "2026-08-10T08:00:00Z", 0, 30)],
  });
  assert.equal(result.merged_busy_intervals.length, 1);
  assert.equal(result.eligible_event_refs.length, 0);
  assert.equal(result.conflicts[0].reason, "outside_window");
});
