// lib/transit.test.js — C2 RED (VCSDD life-manager-cost-connect-reliability).
// Tests the FREE Japan transit router (api.transit.ls8h.com) that replaces Google Routes Pro for JP.
// Pure functions only: parse a real committed /plan fixture, decide JP via a deterministic bbox, and
// pick transit-vs-google. NO network here (network is exercised in the no-mock E2E, not in RED).
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  parseTransitPlan,
  isJapanGeo,
  chooseRouter,
} = require("./transit.js"); // does not exist yet → RED

const FIX = path.join(
  __dirname,
  "../../../.vcsdd/features/life-manager-cost-connect-reliability/evidence/fixtures/transit-plan-tokyo-shinjuku.json"
);
const plan = JSON.parse(fs.readFileSync(FIX, "utf8"));

test("parseTransitPlan: best journey → {durationSecs, legs, transferCount}", () => {
  const r = parseTransitPlan(plan);
  // fixture journey[0] = 中央線快速, durationSecs 1029, 0 transfers
  assert.equal(typeof r.durationSecs, "number");
  assert.ok(r.durationSecs > 0 && r.durationSecs < 7200);
  assert.equal(r.durationSecs, 1090); // door-to-door = 1029 duration(incl egress) + 61 access (FIND-101: no egress double-count)
  assert.ok(Array.isArray(r.legs) && r.legs.length >= 1);
  assert.equal(r.legs[0].mode, "rail");
  assert.equal(r.transferCount, 0);
});

test("parseTransitPlan: no journeys → null (caller falls back to Google)", () => {
  assert.equal(parseTransitPlan({ journeys: [] }), null);
  assert.equal(parseTransitPlan({}), null);
});

test("isJapanGeo: JP bbox (lat 24–46, lon 122–146)", () => {
  assert.equal(isJapanGeo(35.681, 139.767), true); // Tokyo
  assert.equal(isJapanGeo(43.06, 141.35), true); // Sapporo
  assert.equal(isJapanGeo(26.21, 127.68), true); // Naha
  assert.equal(isJapanGeo(40.748, -73.985), false); // NYC (lon out) — /plan returns walk journeys anyway, so bbox is the gate
  assert.equal(isJapanGeo(51.5, -0.12), false); // London
});

test("chooseRouter: both endpoints JP → 'transit', else 'google'", () => {
  assert.equal(chooseRouter({ lat: 35.681, lon: 139.767 }, { lat: 35.69, lon: 139.70 }), "transit");
  assert.equal(chooseRouter({ lat: 35.681, lon: 139.767 }, { lat: 40.73, lon: -73.93 }), "google"); // mixed
  assert.equal(chooseRouter({ lat: 40.748, lon: -73.985 }, { lat: 40.73, lon: -73.93 }), "google"); // both non-JP
});

test("isJapanGeo: exact bbox boundaries 24/46/122/146 inclusive, just-outside excluded — FIND-001", () => {
  assert.equal(isJapanGeo(24, 122), true);
  assert.equal(isJapanGeo(46, 146), true);
  assert.equal(isJapanGeo(23.999, 130), false);
  assert.equal(isJapanGeo(46.001, 130), false);
  assert.equal(isJapanGeo(35, 121.999), false);
  assert.equal(isJapanGeo(35, 146.001), false);
});

test("parseTransitPlan: picks EARLIEST ARRIVAL, not journeys[0] — FIND-006", () => {
  const plan = { journeys: [
    { departureSecs: 100, arrivalSecs: 900, durationSecs: 800, transferCount: 1, legs: [{ mode: "rail" }] }, // first, LATER arrival
    { departureSecs: 200, arrivalSecs: 700, durationSecs: 500, transferCount: 0, legs: [{ mode: "rail" }] }, // earliest arrival
  ] };
  const r = parseTransitPlan(plan);
  assert.equal(r.durationSecs, 500); // the 2nd journey, proving it's not journeys[0]
});

test("parseTransitPlan: preserves anchor, walking, fare, nullable provider facts, and ordered steps", () => {
  const r = parseTransitPlan({
    date: "20260809",
    timezone: "Asia/Tokyo",
    provider: "transit.ls8h",
    computedAt: "2026-08-08T06:00:00.000Z",
    journeys: [{
      departureSecs: 8 * 3600,
      arrivalSecs: 9 * 3600 + 5 * 60,
      durationSecs: 3600,
      accessWalkSecs: 420,
      egressWalkSecs: 300,
      transferCount: 1,
      fare: { currency: "JPY", amount: 210, medium: "IC" },
      legs: [
        {
          kind: "walk", mode: "walk", from: { name: "Home" }, to: { name: "Station" },
          departureSecs: 8 * 3600, arrivalSecs: 8 * 3600 + 420,
          geometry: { type: "LineString", coordinates: [] },
        },
        {
          kind: "transit", mode: "rail", routeName: "Yamanote", headsign: "Shibuya",
          from: { name: "Station" }, to: { name: "Shibuya" }, platform: null,
          departureSecs: 8 * 3600 + 480, arrivalSecs: 8 * 3600 + 3600,
        },
      ],
    }],
  });
  assert.equal(r.provider, "transit.ls8h");
  assert.equal(r.timezone, "Asia/Tokyo");
  assert.equal(r.computedAt, "2026-08-08T06:00:00.000Z");
  assert.equal(r.durationSecs, 4020); // provider journey + access, egress is already in arrival
  assert.equal(r.accessWalkSecs, 420);
  assert.equal(r.egressWalkSecs, 300);
  assert.equal(r.transferCount, 1);
  assert.deepEqual(r.fare, { currency: "JPY", amount: 210, medium: "IC" });
  assert.equal(r.steps.length, 2);
  assert.equal(r.steps[0].mode, "walk");
  assert.equal(r.steps[1].service, "Yamanote");
  assert.equal(r.steps[1].headsign, "Shibuya");
  assert.equal(r.steps[1].platform, null);
  assert.equal(r.steps[1].from, "Station");
  assert.equal(r.steps[1].to, "Shibuya");
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[1], "entrance"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[1], "bestCar"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[1], "crowding"), false);
  assert.deepEqual(r.availability, { platform: false, fare: true, geometry: true });
});

test("parseTransitPlan: missing nullable facts stay null instead of guessed text", () => {
  const r = parseTransitPlan({
    date: "20260809", timezone: "UTC",
    journeys: [{ departureSecs: 10, arrivalSecs: 20, durationSecs: 10, legs: [{ mode: "rail" }] }],
  });
  assert.equal(r.fare, null);
  assert.equal(r.steps[0].platform, null);
  assert.equal(r.steps[0].geometry, null);
  assert.equal(r.availability.fare, false);
  assert.equal(r.availability.platform, false);
});
