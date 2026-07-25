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

// 12c: between_events is unreachable when the fetch window starts at `now` — an intense block that
// ended 10 minutes ago is exactly what the trough trigger needs to see, and exactly what a
// timeMin=now window can never return. lookbackMs widens the window backwards for the MENTAL read
// without changing any existing caller (default 0 keeps the strict-future contract).
test("lookbackMs=0 (default) keeps the strict-future contract: ended events are excluded", async () => {
  const cal = fakeCalendar([
    { summary: "ended", start: { dateTime: "2026-06-20T22:00:00Z" }, end: { dateTime: "2026-06-20T23:50:00Z" } },
  ]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal });
  assert.equal(evs.length, 0);
});

test("lookbackMs returns an event that ended within the lookback window", async () => {
  // 110-min block that ended 10 min before now: starts far before now, ends inside the lookback.
  const cal = fakeCalendar([
    { summary: "deep work", start: { dateTime: "2026-06-20T22:00:00Z" }, end: { dateTime: "2026-06-20T23:50:00Z" } },
  ]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal, lookbackMs: 35 * 60000 });
  assert.equal(evs.length, 1);
  assert.equal(evs[0].summary, "deep work");
});

test("lookbackMs widens timeMin passed to the transport", async () => {
  let seen = null;
  const cal = { kind: "fake", ready: () => true, async listEventsRaw(_uid, window) { seen = window; return []; } };
  await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal, lookbackMs: 35 * 60000 });
  assert.equal(seen.timeMin, "2026-06-20T23:25:00Z");
});

test("lookbackMs does not resurrect events that ended before the window", async () => {
  const cal = fakeCalendar([
    { summary: "long gone", start: { dateTime: "2026-06-20T20:00:00Z" }, end: { dateTime: "2026-06-20T22:00:00Z" } },
  ]);
  const evs = await fetchUpcomingEvents("uid", { nowMs: now, calendar: cal, lookbackMs: 35 * 60000 });
  assert.equal(evs.length, 0);
});
