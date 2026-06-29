// events.test.js — #74: fetchUpcomingEvents maps the transport's raw items correctly + is decoupled
// from any provider (inject a fake calendar). Run: node --test apps/life-call/lib/events.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { fetchUpcomingEvents } = require("./events.js");

const now = Date.parse("2026-06-21T00:00:00Z");
// a fake transport calendar — proves events.js never touches Composio directly
function fakeCalendar(items) {
  return { kind: "fake", ready: () => true, async listEventsRaw() { return items; } };
}

test("maps timed events to {summary,location,startMs,startIso,endMs,endIso}, sorted, filtered", async () => {
  const cal = fakeCalendar([
    { summary: "B", location: "渋谷", start: { dateTime: "2026-06-21T05:00:00Z" }, end: { dateTime: "2026-06-21T06:00:00Z" } },
    { summary: "A", location: "新宿", start: { dateTime: "2026-06-21T02:00:00Z" }, end: { dateTime: "2026-06-21T03:00:00Z" } },
  ]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, horizonH: 18, calendar: cal });
  assert.equal(evs.length, 2);
  assert.equal(evs[0].summary, "A");           // sorted ascending
  assert.equal(evs[0].startMs, Date.parse("2026-06-21T02:00:00Z"));
  assert.equal(evs[0].endMs, Date.parse("2026-06-21T03:00:00Z"));
  assert.equal(evs[1].location, "渋谷");
});

test("skips all-day (date-only) events — no leave time to compute", async () => {
  const cal = fakeCalendar([{ summary: "holiday", start: { date: "2026-06-21" } }]);
  assert.equal((await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal })).length, 0);
});

test("drops events outside [now, now+horizon]", async () => {
  const cal = fakeCalendar([
    { summary: "past", start: { dateTime: "2026-06-20T00:00:00Z" }, end: { dateTime: "2026-06-20T01:00:00Z" } },
    { summary: "far", start: { dateTime: "2026-06-25T00:00:00Z" }, end: { dateTime: "2026-06-25T01:00:00Z" } },
    { summary: "ok", start: { dateTime: "2026-06-21T05:00:00Z" }, end: { dateTime: "2026-06-21T06:00:00Z" } },
  ]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, horizonH: 18, calendar: cal });
  assert.deepEqual(evs.map((e) => e.summary), ["ok"]);
});

test("empty / no uid → []", async () => {
  assert.deepEqual(await fetchUpcomingEvents("", { calendar: fakeCalendar([]) }), []);
  assert.deepEqual(await fetchUpcomingEvents("uid", { nowMs: now, calendar: fakeCalendar([]) }), []);
});

test("missing endMs → null (not NaN) so departureMs/travel can guard", async () => {
  const cal = fakeCalendar([{ summary: "no-end", location: "x", start: { dateTime: "2026-06-21T05:00:00Z" } }]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal });
  assert.equal(evs[0].endMs, null);
});
