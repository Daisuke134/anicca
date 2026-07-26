// events-history.test.js — 11a runtime: care detection needs the user's OWN visit HISTORY, and the
// fetchUpcomingEvents contract is future-only by design (same unreachable-rule disease as 12c: the
// one thing the detector needs — past visits — is the one thing that fetch can never return).
// fetchCalendarHistory is a dedicated history read with its own contract: [now - historyMs, now],
// all-day events kept (a barber visit logged all-day is still a visit), future events excluded.
// Run: node --test lib/events-history.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { fetchCalendarHistory, CARE_HISTORY_MS } = require("./events.js");

const NOW = Date.parse("2026-07-26T00:00:00Z");

function fakeCalendar(items, capture) {
  return {
    kind: "fake",
    ready: () => true,
    async listEventsRaw(_uid, opts) {
      if (capture) capture.opts = opts;
      return items;
    },
  };
}

test("asks the transport for [now - historyMs, now] — a real look BACK, not forward", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, historyMs: 100 * 86400000, calendar: fakeCalendar([], capture) });
  assert.equal(capture.opts.timeMin, new Date(NOW - 100 * 86400000).toISOString().replace(/\.\d{3}Z$/, "Z"));
  assert.equal(capture.opts.timeMax, new Date(NOW).toISOString().replace(/\.\d{3}Z$/, "Z"));
});

test("default window is ~18 months of history", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, calendar: fakeCalendar([], capture) });
  assert.equal(capture.opts.timeMin, new Date(NOW - CARE_HISTORY_MS).toISOString().replace(/\.\d{3}Z$/, "Z"));
  assert.ok(CARE_HISTORY_MS >= 540 * 86400000, "at least ~18 months back");
});

test("keeps all-day (date-only) events — a care visit logged all-day is still a visit", async () => {
  const cal = fakeCalendar([
    { id: "h1", summary: "散髪", start: { date: "2026-06-21" } },
    { id: "h2", summary: "歯科", location: "青山", start: { dateTime: "2026-05-01T09:00:00Z" }, end: { dateTime: "2026-05-01T10:00:00Z" } },
  ]);
  const events = await fetchCalendarHistory("uid", { nowMs: NOW, calendar: cal });
  assert.deepEqual(events.map((e) => e.id), ["h2", "h1"]); // ascending by start
  assert.equal(events[1].summary, "散髪");
  assert.equal(events[0].location, "青山");
  // detectCalendarCare reads event.start.dateTime || event.start.date — the raw start must survive
  assert.deepEqual(events[1].start, { date: "2026-06-21" });
});

test("drops id-less items and events starting after now — history holds only real past visits", async () => {
  const cal = fakeCalendar([
    { summary: "no-id", start: { dateTime: "2026-05-01T09:00:00Z" } },
    { id: "future", summary: "予約", start: { dateTime: "2026-08-01T09:00:00Z" } },
    { id: "ok", summary: "散髪", start: { dateTime: "2026-05-02T09:00:00Z" } },
  ]);
  const events = await fetchCalendarHistory("uid", { nowMs: NOW, calendar: cal });
  assert.deepEqual(events.map((e) => e.id), ["ok"]);
});

test("no uid → [] (mirrors fetchUpcomingEvents' guard)", async () => {
  assert.deepEqual(await fetchCalendarHistory("", { nowMs: NOW, calendar: fakeCalendar([{ id: "x" }]) }), []);
});
