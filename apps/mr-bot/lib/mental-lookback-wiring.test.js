// 12c: between_events was unreachable in production — the tick fetched events with timeMin=now, so
// an intense block that ENDED (the only thing the trough trigger fires on) was never in the list.
// These tests pin the wiring: the tick fetches with a lookback, hands the full window (including
// recently-ended and in-progress events) to the MENTAL organ, and keeps every other consumer on the
// strict-future list. Run: node --test lib/mental-lookback-wiring.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
process.env.SUPABASE_URL = process.env.SUPABASE_URL || "https://db.example";
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "service";
const scheduler = require("../scheduler.js");

const NOW = Date.parse("2026-07-26T00:00:00Z");
const USER = { uid: "u-look", telegram_chat_id: "1", phone: "+81", call_enabled: false, notifications_enabled: true };
// a 110-min block that ended 10 min ago: exactly what between_events needs to see
const ENDED = { summary: "deep work", location: null, startMs: NOW - 120 * 60000, endMs: NOW - 10 * 60000, startIso: "x", endIso: "y" };
const FUTURE = { summary: "later", location: "渋谷", startMs: NOW + 3 * 3600000, endMs: NOW + 4 * 3600000, startIso: "f", endIso: "g" };

function deps(overrides = {}) {
  return {
    recordDailyPoll: async () => true,
    ...overrides,
  };
}

test("the tick fetch asks for a lookback window at least as wide as the trough", async () => {
  let opts = null;
  await scheduler.wakeUserOnce(USER, NOW, {
    ...deps(),
    fetchUpcomingEvents: async (_uid, o) => { opts = o; return []; },
    mental: async () => null,
    lateNotice: async () => null,
  });
  assert.ok(opts, "fetchUpcomingEvents was called");
  assert.ok(opts.lookbackMs >= 30 * 60000, `lookbackMs must cover TROUGH_AFTER_MS, got ${opts.lookbackMs}`);
});

test("MENTAL sees the ended block; late-notice sees only the future", async () => {
  let mentalEvents = null, lateEvents = null;
  await scheduler.wakeUserOnce(USER, NOW, {
    ...deps(),
    fetchUpcomingEvents: async () => [ENDED, FUTURE],
    lateNotice: async (_u, _n, d) => { lateEvents = d.events; return null; },
    // mentalDeps hands events to the organ via its own fetchUpcomingEvents closure (already shaped)
    mental: async (_u, _n, d) => { mentalEvents = await d.fetchUpcomingEvents(); return null; },
  });
  assert.ok(Array.isArray(mentalEvents), "mental received events");
  assert.equal(mentalEvents.length, 2, "mental sees ended + future");
  const endedShaped = mentalEvents.find((e) => e.endMs === ENDED.endMs);
  assert.ok(endedShaped, "the ended block reaches MENTAL");
  assert.equal(endedShaped.intense, true, "110-min block is shaped intense");
  assert.ok(Array.isArray(lateEvents), "lateNotice received events");
  assert.equal(lateEvents.length, 1, "lateNotice keeps the strict-future list");
  assert.equal(lateEvents[0].startMs, FUTURE.startMs);
});
