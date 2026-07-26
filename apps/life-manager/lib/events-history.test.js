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
      if (capture) {
        capture.opts = opts; // last call
        (capture.all = capture.all || []).push(opts); // every call (the window may be chunked)
      }
      return items;
    },
  };
}

// Sorted [startMs, endMs] spans of every transport call — the union must cover the whole window.
function spansOf(capture) {
  return (capture.all || [])
    .map((o) => [Date.parse(o.timeMin), Date.parse(o.timeMax)])
    .sort((a, b) => a[0] - b[0]);
}

test("asks the transport for [now - historyMs, now] — a real look BACK, not forward", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, historyMs: 100 * 86400000, calendar: fakeCalendar([], capture) });
  assert.equal(capture.opts.timeMin, new Date(NOW - 100 * 86400000).toISOString().replace(/\.\d{3}Z$/, "Z"));
  assert.equal(capture.opts.timeMax, new Date(NOW).toISOString().replace(/\.\d{3}Z$/, "Z"));
});

test("default window is ~18 months of history (union of all transport calls)", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, calendar: fakeCalendar([], capture) });
  const spans = spansOf(capture);
  assert.equal(spans[0][0], NOW - CARE_HISTORY_MS, "oldest call starts at now - CARE_HISTORY_MS");
  assert.equal(spans[spans.length - 1][1], NOW, "newest call ends at now");
  assert.ok(CARE_HISTORY_MS >= 540 * 86400000, "at least ~18 months back");
});

// 🟡 Finding 4: one 548-day ascending-ordered call with maxResults 2500 truncates the RECENT end on
// busy calendars, freezing stale last-visits as false overdues. The transport wrapper exposes no
// pageToken, so the window is split into ≤3 sequential chunks whose union is contiguous.
test("the 18-month window is split into ≤3 contiguous chunks so maxResults cannot eat the recent end", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, calendar: fakeCalendar([], capture) });
  const spans = spansOf(capture);
  assert.ok(spans.length >= 2 && spans.length <= 3, `expected 2-3 chunks, got ${spans.length}`);
  for (let i = 1; i < spans.length; i += 1) {
    assert.equal(spans[i][0], spans[i - 1][1], "chunks must be contiguous — no gap loses visits");
  }
});

test("busy calendar (> maxResults events): the NEWEST events survive, and merged chunks never duplicate ids", async () => {
  const DAY = 86400000;
  const all = [];
  for (let i = 0; i < 3000; i += 1) {
    // 3000 events spread across the full window — a single 2500-capped ascending call drops the newest
    const startMs = NOW - CARE_HISTORY_MS + Math.floor(i * ((CARE_HISTORY_MS - DAY) / 3000));
    all.push({ id: `e${i}`, summary: i === 2999 ? "散髪" : "予定", start: { dateTime: new Date(startMs).toISOString() } });
  }
  const cal = {
    kind: "fake",
    ready: () => true,
    // honors [timeMin, timeMax] and truncates ASCENDING at maxResults — Google's orderBy=startTime behavior
    async listEventsRaw(_uid, { timeMin, timeMax, maxResults }) {
      const lo = Date.parse(timeMin); const hi = Date.parse(timeMax);
      const inWindow = all.filter((e) => { const t = Date.parse(e.start.dateTime); return t >= lo && t <= hi; });
      return maxResults ? inWindow.slice(0, maxResults) : inWindow;
    },
  };
  const events = await fetchCalendarHistory("uid", { nowMs: NOW, calendar: cal });
  assert.ok(events.some((e) => e.id === "e2999"), "the newest visit must survive truncation — it IS the last-visit date");
  assert.equal(new Set(events.map((e) => e.id)).size, events.length, "chunk-boundary events must merge, not duplicate");
});

// 🔴 Finding 1 (transport leg): the history path must distinguish failure from empty. The composio
// wake path keeps its swallow-to-[] (load-bearing there); the history read passes strict and lets a
// transport failure PROPAGATE instead of returning a fake empty calendar.
test("history read is STRICT: passes strict to the transport and propagates its failure", async () => {
  const capture = {};
  await fetchCalendarHistory("uid", { nowMs: NOW, calendar: fakeCalendar([], capture) });
  for (const call of capture.all) assert.equal(call.strict, true, "every history chunk must be a strict read");
  await assert.rejects(
    () => fetchCalendarHistory("uid", {
      nowMs: NOW,
      calendar: { kind: "fake", ready: () => true, async listEventsRaw() { throw new Error("api down"); } },
    }),
    /api down/,
  );
});

test("composio transport: strict mode throws on API failure; the non-strict wake path still swallows to []", async () => {
  const { makeComposioCalendar } = require("./transport/calendar-composio.js");
  const origFetch = globalThis.fetch;
  const origKey = process.env.COMPOSIO_API_KEY;
  delete process.env.COMPOSIO_API_KEY; // the keyless case below must really be keyless
  try {
    globalThis.fetch = async () => ({ json: async () => ({ successful: false, error: "quota exceeded" }) });
    const cal = makeComposioCalendar({ apiKey: "k", recordCall: () => false });
    assert.deepEqual(await cal.listEventsRaw("uid", { timeMin: "2026-01-01T00:00:00Z", timeMax: "2026-07-26T00:00:00Z" }), [],
      "wake path contract unchanged: failure swallows to []");
    await assert.rejects(
      () => cal.listEventsRaw("uid", { timeMin: "2026-01-01T00:00:00Z", timeMax: "2026-07-26T00:00:00Z", strict: true }),
      /quota exceeded/,
    );
    globalThis.fetch = async () => { throw new Error("network down"); };
    await assert.rejects(
      () => cal.listEventsRaw("uid", { timeMin: "2026-01-01T00:00:00Z", timeMax: "2026-07-26T00:00:00Z", strict: true }),
      /network down/,
    );
    const keyless = makeComposioCalendar({ apiKey: "", recordCall: () => false });
    await assert.rejects(
      () => keyless.listEventsRaw("uid", { strict: true }),
      /key|uid|ready/i,
    );
  } finally {
    globalThis.fetch = origFetch;
    if (origKey !== undefined) process.env.COMPOSIO_API_KEY = origKey;
  }
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
