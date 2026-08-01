// lib/travel-transit-wire.test.js — C2/C3 WIRE (integration into travel.js). directionsMinutes must
// try the FREE JP transit path first (geocode src/dst → JP bbox → api.transit.ls8h.com /plan, cached),
// and fall back to Google only when transit doesn't resolve. Uses injected seams (no network).
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const travel = require("./travel.js");
const { makeRouteCache } = require("./route-cache.js");
const freshCache = () => makeRouteCache({ store: new Map(), ttlMs: 600000 });

// A fake geocoder: JP addresses → JP geo; "NYC" → non-JP geo; "" → null.
const fakeGeocode = async (addr) => {
  if (!addr) return null;
  if (addr.includes("NYC")) return { lat: 40.73, lon: -73.93 };
  return { lat: 35.681, lon: 139.767 }; // any JP-ish address
};
// A fake transit fetch returning the committed fixture shape (17-min 中央線快速).
const fakeTransitFetch = async () => ({
  journeys: [{ departureSecs: 100, arrivalSecs: 1129, durationSecs: 1029, transferCount: 0, legs: [{ mode: "rail", routeName: "中央線快速" }] }],
});

test("directionsMinutes: JP src+dst → uses transit (17 min), NO Google call", async () => {
  let googleCalled = false;
  const mins = await travel.directionsMinutes("新宿区A", "渋谷区B", "mapsKey", Date.now() + 3600000, Date.now(), false, {
    _geocode: fakeGeocode,
    _transitFetch: fakeTransitFetch,
    _directionsMinutesGoogle: async () => { googleCalled = true; return 45; },
    _routeCache: freshCache(),
  });
  assert.equal(mins, 17); // 1029s → 17 min (ceil), from transit
  assert.equal(googleCalled, false); // free path — Google not called
});

test("directionsMinutes: non-JP dst → falls back to Google", async () => {
  let googleCalled = false;
  const mins = await travel.directionsMinutes("新宿区A", "NYC place", "mapsKey", Date.now() + 3600000, Date.now(), false, {
    _geocode: fakeGeocode,
    _transitFetch: fakeTransitFetch,
    _directionsMinutesGoogle: async () => { googleCalled = true; return 45; },
    _routeCache: freshCache(),
  });
  assert.equal(googleCalled, true);
  assert.equal(mins, 45);
});

test("directionsMinutes: transit 0 journeys → Google fallback", async () => {
  let googleCalled = false;
  const mins = await travel.directionsMinutes("新宿区A", "渋谷区B", "mapsKey", Date.now() + 3600000, Date.now(), false, {
    _geocode: fakeGeocode,
    _transitFetch: async () => ({ journeys: [] }),
    _directionsMinutesGoogle: async () => { googleCalled = true; return 30; },
    _routeCache: freshCache(),
  });
  assert.equal(googleCalled, true);
  assert.equal(mins, 30);
});

test("directionsMinutes: repeated ticks (same event) call the provider ONCE — FIND-002 cache", async () => {
  let transitCalls = 0;
  const cache = freshCache();
  const opts = {
    _geocode: fakeGeocode,
    _transitFetch: async () => { transitCalls++; return fakeTransitFetch(); },
    _directionsMinutesGoogle: async () => 45,
    _routeCache: cache,
  };
  const at = Date.now() + 3600000; // ev.startMs is CONSTANT across the 60s ticks
  await travel.directionsMinutes("新宿区A", "渋谷区B", "k", at, Date.now(), false, opts);
  await travel.directionsMinutes("新宿区A", "渋谷区B", "k", at, Date.now() + 60000, false, opts); // next tick, same event
  assert.equal(transitCalls, 1); // second tick is a cache hit
});

// C3 REGRESSION (2026-08-02, found while wiring #2c): the address→geo memo above directionsMinutes
// was READ but never WRITTEN — `_geoMemo.has()` with no matching `.set()` — so it never once
// prevented a geocode. Every other test in this file injects `_geocode`, which is precisely why a
// dead cache could sit here unnoticed; this one drives the REAL geocodeAddress.
//
// It matters now because #2c removed wakeTick's `call_enabled` filter (§5.3 makes phone-less the
// default cohort), so resolveDeparture — and these two geocodes per event — runs for the WHOLE fleet
// on every 60s tick instead of only for phone users.
test("directionsMinutes geocodes a repeated address ONCE (the C3 memo must actually memoize)", async () => {
  const originalFetch = global.fetch;
  let geocodes = 0;
  const unique = `渋谷区メモ試験-${Date.now()}`; // the memo is process-lifetime; never reuse a key
  global.fetch = async (u) => {
    const s = String(u);
    if (s.includes("/geocode/")) {
      geocodes++;
      return { ok: true, json: async () => ({ results: [{ geometry: { location: { lat: 35.66, lng: 139.70 } } }] }) };
    }
    return { ok: true, json: async () => ({}) };
  };
  try {
    const at = Date.now() + 3600000;
    for (let i = 0; i < 5; i++) {
      await travel.directionsMinutes(unique, `${unique}-dst`, "mapsKey", at, Date.now(), false, {
        _transitFetch: async () => null,
        _directionsMinutesGoogle: async () => 30,
        _routeCache: freshCache(), // a fresh route cache each tick, so ONLY the geo memo is under test
      });
    }
    assert.equal(geocodes, 2, "two distinct addresses, geocoded once each — not once per tick");
  } finally {
    global.fetch = originalFetch;
  }
});
