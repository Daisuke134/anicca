// lib/travel-transit-wire.test.js — C2/C3 WIRE (integration into travel.js). directionsMinutes must
// try the FREE JP transit path first (geocode src/dst → JP bbox → api.transit.ls8h.com /plan, cached),
// and fall back to Google only when transit doesn't resolve. Uses injected seams (no network).
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const travel = require("./travel.js");

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
  });
  assert.equal(googleCalled, true);
  assert.equal(mins, 30);
});
