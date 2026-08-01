"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3 row 1c, §3.1 — claim ownership.
//
// WHY ITS OWN FILE. test/wake-miss-record.test.js is about the lm_wake_miss LEDGER (row 1b: a wake
// we owed and did not deliver leaves a reasoned trace), and it drives wakeUserOnce through injected
// deps. This file is about a different property — that a release can prove it owns the row it
// deletes — and two of its three cases have to reach the REAL claimWake/releaseWake, which talk to
// PostgREST directly and are stubbed at the fetch seam instead. Folding them into the miss ledger
// file would mix two harness styles and blur what each file pins.
//
// THE HARM BEING PREVENTED IS A SECOND PHONE CALL. forEachUserSafe's timeout does not abort the work
// it abandons, so a hung placeCall outlives its tick and its late releaseWake could delete a LATER
// tick's successful claim — after which the next tick re-claims and rings the user again. Dropping
// the wake budget from 90s to 20s made the abandonment ~4.5x more likely, so this got worse, not
// better. A duplicate call is user-visible harm, so the claim gets an identity rather than a
// narrower race window.
//
// Run: node --test test/wake-claim-token.test.js
const { test } = require("node:test");
const assert = require("node:assert");

process.env.LM_CALL_SECRET = "unit_secret";
process.env.PUBLIC_WSS = "wss://life-call.invalid";
// claimWake/releaseWake read SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY from process.env via SUPA(),
// which no-ops without them — set before require, exactly as lib/ch1-atomic-dedup.test.js does.
process.env.SUPABASE_URL = process.env.SUPABASE_URL || "http://supa.invalid";
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "service-role-key";

const { claimWake, releaseWake, wakeCallOnce } = require("../scheduler.js");

// An injected fetchImpl rather than a global stub: these two functions are the only ones in
// scheduler.js that call fetch for the claim ledger, and monkey-patching globalThis.fetch leaks
// across the whole test process (lib/wake-miss.test.js already sets the injected-seam precedent).
function stubFetch(statuses) {
  const calls = [];
  let i = 0;
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), method: (init && init.method) || "GET", body: (init && init.body) || "" });
    const status = statuses[Math.min(i++, statuses.length - 1)];
    return { status, ok: status >= 200 && status < 300, json: async () => [] };
  };
  return { fetchImpl, calls };
}

const KEY = "u1|2026-08-05T14:00:00+09:00|5";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

test("a fresh claim returns its own token, and a duplicate claim returns falsy", async () => {
  const fresh = stubFetch([201]);
  const token = await claimWake("u1", KEY, { fetchImpl: fresh.fetchImpl });
  assert.match(String(token), UUID_RE, "201 hands back the identity of THIS claim, not a bare true");
  assert.match(fresh.calls[0].url, /\/rest\/v1\/lm_wake_log$/);
  assert.equal(fresh.calls[0].method, "POST");
  assert.equal(JSON.parse(fresh.calls[0].body).claim_token, token,
    "the token is written to the row, which is what a later release matches on");

  const dup = stubFetch([409]);
  const second = await claimWake("u1", KEY, { fetchImpl: dup.fetchImpl });
  assert.ok(!second, "409 must stay FALSY — every caller gates the dial on `if (!fresh) continue`");
});

test("two claims of the same key never share a token", async () => {
  const a = stubFetch([201]);
  const b = stubFetch([201]);
  const first = await claimWake("u1", KEY, { fetchImpl: a.fetchImpl });
  const second = await claimWake("u1", KEY, { fetchImpl: b.fetchImpl });
  assert.notEqual(first, second, "identity per claim is the whole mechanism; a shared token is none");
});

test("releaseWake given a token DELETEs only the row carrying that token", async () => {
  const s = stubFetch([200]);
  await releaseWake("u1", KEY, "tok-abc", { fetchImpl: s.fetchImpl });
  assert.equal(s.calls[0].method, "DELETE");
  assert.match(s.calls[0].url, /uid=eq\.u1/);
  assert.match(s.calls[0].url, /event_key=eq\.u1%7C2026-08-05T14%3A00%3A00%2B09%3A00%7C5/);
  assert.match(s.calls[0].url, /claim_token=eq\.tok-abc/,
    "without this filter a stale release deletes a LATER tick's successful claim → a second call");
});

test("releaseWake with no token keeps the old unconditional DELETE", async () => {
  // Rows claimed before claim_token existed carry NULL, and `claim_token=eq.<x>` would never match
  // them — so an old claim must still be releasable the way it always was. Narrowing this would
  // strand those rows in lm_wake_log forever, which is the permanently-burnt-slot bug releaseWake
  // was written to fix.
  const s = stubFetch([200]);
  await releaseWake("u1", KEY, undefined, { fetchImpl: s.fetchImpl });
  assert.equal(s.calls[0].method, "DELETE");
  assert.ok(!/claim_token/.test(s.calls[0].url), "no token given → no token filter");
});

test("a claim survives a store that has not run the migration yet", async () => {
  // Deploy order is not atomic: if the code ships before the column exists, PostgREST 400s on the
  // unknown column and EVERY claim fails — a fleet-wide silence of the one thing this product
  // promises. supaUsers already carries this exact fail-safe for wake_policy. Degraded mode is
  // simply today's behaviour: a claim with no identity, released unconditionally.
  const s = stubFetch([400, 201]);
  const token = await claimWake("u1", KEY, { fetchImpl: s.fetchImpl });
  assert.ok(token, "the dial still happens");
  assert.equal(s.calls.length, 2, "it retried");
  assert.equal("claim_token" in JSON.parse(s.calls[1].body), false, "the retry drops the unknown column");
  assert.equal(typeof token, "boolean", "and says so: no identity to release with");
});

// ── the wiring: the dial-failure path must release with what it claimed with ──────────────────────
const MINUTE = 60_000;
const EVENT_START_ISO = "2026-08-05T14:00:00+09:00";
const EVENT_START_MS = Date.parse(EVENT_START_ISO);
const DEPARTURE_MS = EVENT_START_MS - 40 * MINUTE; // 35 min travel + resolveDeparture's 5-min buffer

const USER = {
  uid: "token-user",
  name: "Token User",
  phone: "+810000000000",
  home_address: "東京都渋谷区",
  call_language: "ja",
  daily_automation_enabled: true,
  call_enabled: true,
  notifications_enabled: false,
};

const EVENT = {
  id: "token-event",
  summary: "新宿で打ち合わせ",
  location: "新宿",
  startMs: EVENT_START_MS,
  startIso: EVENT_START_ISO,
  endMs: EVENT_START_MS + 60 * MINUTE,
};

test("a failed dial releases with the token it claimed with, not a bare key", async () => {
  const released = [];
  await wakeCallOnce(USER, DEPARTURE_MS - 5 * MINUTE, {
    recordDailyPoll: async () => true,
    fetchUpcomingEvents: async () => [{ ...EVENT }],
    mapsKey: "token-maps-key",
    directionsMinutes: async () => 35,
    claimWake: async () => "claim-token-xyz",
    placeCall: async () => ({ ok: false, error: "balance too low" }),
    releaseWake: async (uid, key, claimToken) => released.push({ uid, key, claimToken }),
    recordWakeMiss: async () => ({ ok: true }),
    alertLowBalance: async () => {},
  });

  assert.equal(released.length, 1, "the claim is still released so the next tick retries");
  assert.equal(released[0].key, `${USER.uid}|${EVENT_START_ISO}|5`);
  assert.equal(released[0].claimToken, "claim-token-xyz",
    "the token travels from claim to release — a release that cannot name its claim can delete someone else's");
});
