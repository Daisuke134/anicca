"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3 row 1c — the done receipt.
//
// The measured failure (§3.1): late and mental ran BEFORE the dial inside one 90s per-user budget, so
// two slow organs abandoned the user before a call was ever attempted. These tests pin the property
// that fixes it — the dial does not run the organs at all — and pin the constraint that made method A
// worth choosing: the split must not double Composio calls.
//
// Run: node --test test/wake-loop-isolation.test.js
const { test } = require("node:test");
const assert = require("node:assert");

process.env.LM_CALL_SECRET = "unit_secret";
process.env.PUBLIC_WSS = "wss://life-call.invalid";

const {
  wakeCallOnce, organsUserOnce, WAKE_USER_TIMEOUT_MS, forEachUserSafe,
} = require("../scheduler.js");
const { clearEvents, getEvents } = require("../lib/event-cache.js");

const MINUTE = 60_000;
const EVENT_START_ISO = "2026-08-05T14:00:00+09:00";
const EVENT_START_MS = Date.parse(EVENT_START_ISO);
const TRAVEL_MIN = 35; // + resolveDeparture's 5-min buffer → departure = start − 40 min
const DEPARTURE_MS = EVENT_START_MS - 40 * MINUTE;

const USER = {
  uid: "iso-user",
  name: "Iso User",
  phone: "+810000000000",
  home_address: "東京都渋谷区",
  call_language: "ja",
  daily_automation_enabled: true,
  call_enabled: true,
  notifications_enabled: false,
};

const EVENT = {
  id: "iso-event",
  summary: "新宿で打ち合わせ",
  location: "新宿",
  startMs: EVENT_START_MS,
  startIso: EVENT_START_ISO,
  endMs: EVENT_START_MS + 60 * MINUTE,
};

function deps({ slowOrganMs = 0, fetches } = {}) {
  const dialed = [];
  const held = new Set();
  const stall = async () => { if (slowOrganMs) await new Promise((r) => setTimeout(r, slowOrganMs)); return null; };
  return {
    dialed,
    deps: {
      recordDailyPoll: async () => true,
      fetchUpcomingEvents: async () => { if (fetches) fetches.push(1); return [{ ...EVENT }]; },
      directionsMinutes: async () => TRAVEL_MIN,
      mapsKey: "iso-maps-key",
      claimWake: async (_uid, key) => { if (held.has(key)) return false; held.add(key); return true; },
      placeCall: async () => { dialed.push(Date.now()); return { ok: true, ccid: "iso-1" }; },
      releaseWake: async () => {},
      alertLowBalance: async () => {},
      recordWakeMiss: async () => ({ ok: true }),
      wakeWasClaimed: async (_uid, key) => held.has(key),
      // every organ stalls
      lateNotice: stall, mental: stall, care: stall, diet: stall, dietNudge: stall,
      preceptsMirror: stall, precepts: stall, relations: stall,
      log: () => {},
    },
  };
}

test("the dial half does not run a single organ — a stalled organ cannot reach it", async () => {
  clearEvents();
  const h = deps({ slowOrganMs: 5000 });
  const started = Date.now();
  await wakeCallOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
  const elapsed = Date.now() - started;
  assert.equal(h.dialed.length, 1, "the call is placed");
  assert.ok(elapsed < 1000, `the dial path must not wait on organs (took ${elapsed}ms)`);
});

test("a hung bookkeeping write cannot hold the dial — the daily poll ledger is not awaited", async () => {
  // Same failure class as the test above, in miniature and easier to miss: recordDailyComposioPoll
  // is 1-2 Supabase round trips with no timeout and no AbortController, and it sat AWAITED in front
  // of the dial. It records that a calendar poll happened today — accounting, not a precondition —
  // so a slow store must cost the ledger, never the phone call. Narrowing the budget from 90s to 20s
  // made this worse, not better: the same stall now abandons the user 4.5x sooner.
  clearEvents();
  const h = deps();
  h.deps.recordDailyPoll = () => new Promise(() => {}); // never resolves, never rejects
  const started = Date.now();
  await wakeCallOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
  const elapsed = Date.now() - started;
  assert.equal(h.dialed.length, 1, "the call is still placed");
  assert.ok(elapsed < 1000, `the dial path must not wait on bookkeeping (took ${elapsed}ms)`);
});

test("a failing daily-poll ledger is logged, not swallowed, and never crashes the dial", async () => {
  // Fire-and-forget without a .catch turns a Supabase blip into an unhandled rejection that can take
  // the whole scheduler process down — a worse outcome than the blocking call it replaced. And a
  // .catch that swallows silently recreates the invisibility this whole spec exists to end.
  clearEvents();
  const h = deps();
  h.deps.recordDailyPoll = async () => { throw new Error("supabase 503"); };
  const errors = [];
  const originalError = console.error;
  console.error = (...args) => errors.push(args.join(" "));
  try {
    await wakeCallOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
    await new Promise((r) => setImmediate(r)); // let the detached rejection settle
  } finally {
    console.error = originalError;
  }
  assert.equal(h.dialed.length, 1, "the call is still placed");
  assert.ok(
    errors.some((line) => /supabase 503/.test(line)),
    `the ledger failure is reported, not hidden (saw ${JSON.stringify(errors)})`,
  );
});

test("the wake loop's per-user budget is its own, and far below the organ budget", () => {
  assert.equal(WAKE_USER_TIMEOUT_MS, 20000);
  assert.ok(WAKE_USER_TIMEOUT_MS < 90000, "the shared 90s budget was sized for the care organ, not the dial");
});

test("the dial publishes the calendar so the organ tick does not fetch it again", async () => {
  clearEvents();
  const fetches = [];
  const h = deps({ fetches });
  const now = DEPARTURE_MS - 5 * MINUTE;
  await wakeCallOnce(USER, now, h.deps);
  assert.equal(fetches.length, 1, "the wake half fetches once");
  assert.ok(getEvents(USER.uid, now), "and publishes what it fetched");

  await organsUserOnce(USER, now, h.deps);
  assert.equal(fetches.length, 1, "the organ half reuses it — the split must not double Composio calls");
});

test("the organ half still fetches when nothing was published (first tick after a restart)", async () => {
  clearEvents();
  const fetches = [];
  const h = deps({ fetches });
  await organsUserOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
  assert.equal(fetches.length, 1, "a cache miss falls back to a real fetch rather than skipping the organs");
});

test("one user blowing the wake budget does not stop the next user's dial", async () => {
  const order = [];
  await forEachUserSafe(
    [{ uid: "slow" }, { uid: "fast" }],
    "wake",
    async (u) => {
      if (u.uid === "slow") await new Promise((r) => setTimeout(r, 200));
      order.push(u.uid);
    },
    50, // a 50ms budget stands in for the real 20s one
  );
  assert.deepEqual(order, ["fast"], "the slow user is abandoned; the fast user is still served");
});

// spec §3 row 1e. The organ tick inherited `call_enabled !== false` from the days when the dial lived
// inside it. Now that the dial has its own loop (which filters on `call_enabled` itself), that copy
// only does harm: care/diet/mental/precepts/relations have nothing to do with a phone, and spec §5.3
// promises the phone-less user the same product over Telegram. The organ tick's own care comment says
// so — "Still runs for call-disabled users" — while the filter above it said otherwise.
const { tick, wakeTick } = require("../scheduler.js");

test("the organ tick serves a user who gave no phone number", async () => {
  const served = [];
  await tick({
    listUsers: async () => [
      { uid: "has-phone", daily_automation_enabled: true, call_enabled: true },
      { uid: "no-phone", daily_automation_enabled: true, call_enabled: false },
    ],
    organs: async (u) => { served.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(served, ["has-phone", "no-phone"],
    "organs are not a phone feature — spec §5.3 promises this user the same product over Telegram");
});

test("the organ tick still respects the one switch that means 'run nothing for me'", async () => {
  const served = [];
  await tick({
    listUsers: async () => [{ uid: "opted-out", daily_automation_enabled: false, call_enabled: true }],
    organs: async (u) => { served.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(served, [], "daily_automation_enabled=false is the real opt-out and still holds");
});

test("the wake tick keeps its own call_enabled filter — dialing a user with no phone is nonsense", async () => {
  const dialled = [];
  await wakeTick({
    listUsers: async () => [
      { uid: "has-phone", daily_automation_enabled: true, call_enabled: true },
      { uid: "no-phone", daily_automation_enabled: true, call_enabled: false },
    ],
    wake: async (u) => { dialled.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(dialled, ["has-phone"], "the filter belongs to the dial, and stays there");
});

// spec §5.2.1 / §5.3 — the phone is opt-IN now, not opt-out.
//
// The `!== false` idiom encodes "on unless refused", which is the exact opposite of what the spec
// now says: a user who has expressed no preference gets no call. Three shapes all mean "expressed no
// preference" and every one of them used to dial: no preference row at all, a row whose column is
// SQL NULL, and (before RUNTIME_DEFAULTS flips) a merged default of true. Only `=== true` refuses
// all three while still honouring the person who deliberately switched calls on.
test("a user who never asked for calls is not dialled; an explicit opt-in still is", async () => {
  const dialled = [];
  await wakeTick({
    listUsers: async () => [
      { uid: "opted-in", daily_automation_enabled: true, call_enabled: true },
      { uid: "no-preference-row", daily_automation_enabled: true },
      { uid: "null-column", daily_automation_enabled: true, call_enabled: null },
      { uid: "opted-out", daily_automation_enabled: true, call_enabled: false },
    ],
    wake: async (u) => { dialled.push(u.uid); },
    now: 0,
  });
  assert.deepEqual(dialled, ["opted-in"],
    "silence is not consent to be phoned — §5.2.1 makes the phone an extra, and Telegram the default");
});

// The tick filter is not the only door. wakeUserOnce (the Inngest per-user path) calls wakeCallOnce
// directly and never passes through wakeTick's filter, so the dial half must refuse for itself.
test("the dial half itself refuses a user who never asked for calls", async () => {
  clearEvents();
  const h = deps();
  await wakeCallOnce({ ...USER, call_enabled: undefined }, DEPARTURE_MS - 5 * MINUTE, h.deps);
  assert.equal(h.dialed.length, 0, "the Inngest per-user path bypasses wakeTick — this gate is the last one");

  const optedIn = deps();
  await wakeCallOnce({ ...USER, call_enabled: true }, DEPARTURE_MS - 5 * MINUTE, optedIn.deps);
  assert.equal(optedIn.dialed.length, 1, "and the person who switched calls on is still called");
});
