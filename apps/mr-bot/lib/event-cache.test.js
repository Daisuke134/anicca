"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3.1 (method A).
//
// Splitting the wake call onto its own tick would double Composio usage if both loops fetched the
// calendar: lib/calendar-cache.js keys on a MINUTE bucket derived from now, so two loops running at
// different phases never share an entry. Instead the wake tick OWNS the fetch and publishes here;
// the organ tick reads. This cache is deliberately in-process and tiny — it is a hand-off between
// two timers in one process, not a durable store.
//
// Run: node --test lib/event-cache.test.js
const { test } = require("node:test");
const assert = require("node:assert");

const { putEvents, getEvents, clearEvents, EVENT_CACHE_TTL_MS } = require("./event-cache.js");

test("what the wake tick publishes is what the organ tick reads", () => {
  clearEvents();
  const events = [{ id: "e1" }];
  putEvents("u1", events, 1000);
  assert.deepEqual(getEvents("u1", 1000), events);
});

test("a stale entry is not served — a caller must fetch rather than act on old calendar data", () => {
  clearEvents();
  putEvents("u1", [{ id: "e1" }], 1000);
  assert.equal(getEvents("u1", 1000 + EVENT_CACHE_TTL_MS + 1), null);
});

test("one user's events are never served to another", () => {
  clearEvents();
  putEvents("u1", [{ id: "e1" }], 1000);
  assert.equal(getEvents("u2", 1000), null);
});

test("a miss is null, never an empty array — 'no events' and 'never fetched' must not look alike", () => {
  clearEvents();
  assert.equal(getEvents("nobody", 1000), null);
  putEvents("u1", [], 1000);
  assert.deepEqual(getEvents("u1", 1000), []);
});

test("publishing again replaces the entry and restarts its freshness", () => {
  clearEvents();
  putEvents("u1", [{ id: "old" }], 1000);
  putEvents("u1", [{ id: "new" }], 1000 + EVENT_CACHE_TTL_MS);
  // Read PAST the first entry's expiry: had the republish kept the original timestamp, this would
  // now be stale and return null. So this pins BOTH halves — the value swapped AND the clock reset.
  assert.deepEqual(getEvents("u1", 1000 + EVENT_CACHE_TTL_MS + 1), [{ id: "new" }]);
});
