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

test("directionsRoute: Transit receives the event anchor and accepted result never calls Google", async () => {
  let anchor;
  let googleCalls = 0;
  const eventAt = Date.parse("2026-08-09T09:00:00+09:00");
  const route = await travel.directionsRoute("新宿区A", "渋谷区B", "mapsKey", eventAt, eventAt - 60000, false, {
    _geocode: fakeGeocode,
    _transitFetch: async (_from, _to, options) => {
      anchor = options;
      return {
        date: "20260809", timezone: "Asia/Tokyo", journeys: [{
          departureSecs: 100, arrivalSecs: 1000, durationSecs: 900,
          accessWalkSecs: 120, egressWalkSecs: 60, transferCount: 1,
          fare: { currency: "JPY", amount: 210 },
          legs: [{ mode: "rail", routeName: "Ginza", headsign: "渋谷", departureSecs: 100, arrivalSecs: 900 }],
        }],
      };
    },
    _directionsMinutesGoogle: async () => { googleCalls += 1; return 45; },
    _routeCache: freshCache(),
    _timezone: "Asia/Tokyo",
  });
  assert.equal(route.provider, "transit");
  assert.equal(route.route.transferCount, 1);
  assert.equal(route.route.accessWalkSecs, 120);
  assert.equal(route.minutes, 17);
  assert.equal(anchor.eventAt, new Date(eventAt).toISOString());
  assert.equal(anchor.timezone, "Asia/Tokyo");
  assert.equal(anchor.direction, "outbound");
  assert.equal(googleCalls, 0);
});

test("directionsRoute: return query uses depart-at semantics with the same event anchor", async () => {
  let anchor;
  const eventEnd = Date.parse("2026-08-09T18:00:00+09:00");
  const route = await travel.directionsRoute("渋谷区B", "新宿区A", "mapsKey", eventEnd, eventEnd - 60000, true, {
    _geocode: fakeGeocode,
    _transitFetch: async (_from, _to, options) => {
      anchor = options;
      return { date: "20260809", timezone: "Asia/Tokyo", journeys: [{ departureSecs: 100, arrivalSecs: 700, durationSecs: 600, legs: [] }] };
    },
    _routeCache: freshCache(),
    _timezone: "Asia/Tokyo",
  });
  assert.equal(route.provider, "transit");
  assert.equal(route.minutes, 10);
  assert.equal(anchor.eventAt, new Date(eventEnd).toISOString());
  assert.equal(anchor.direction, "return");
});
