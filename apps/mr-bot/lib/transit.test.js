// lib/transit.test.js — C2 RED (VCSDD mr-bot-cost-connect-reliability).
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
  "../../../.vcsdd/features/mr-bot-cost-connect-reliability/evidence/fixtures/transit-plan-tokyo-shinjuku.json"
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

test("parseTransitPlan: arrival anchor selects latest viable departure and normalizes overnight times", () => {
  const r = parseTransitPlan({
    date: "20260809",
    type: "arrival",
    timezone: "Asia/Tokyo",
    journeys: [
      {
        departureSecs: 23 * 3600 + 20 * 60,
        arrivalSecs: 24 * 3600 + 30 * 60,
        durationSecs: 4200,
        accessWalkSecs: 300,
        egressWalkSecs: 120,
        transferCount: 1,
        fare: { currency: "JPY", ticket: 220, ic: 216 },
        legs: [{
          kind: "transit", mode: "rail", routeName: "中央線", trainType: "快速", headsign: "高尾",
          from: { name: "東京", platformCode: "1番線" },
          to: { name: "新宿", platformCode: "3番線" },
          departureSecs: 23 * 3600 + 20 * 60,
          arrivalSecs: 24 * 3600 + 15 * 60,
        }],
      },
      {
        departureSecs: 22 * 3600 + 30 * 60,
        arrivalSecs: 23 * 3600 + 50 * 60,
        durationSecs: 4800,
        legs: [{ kind: "transit", mode: "rail", routeName: "遅い線" }],
      },
      {
        departureSecs: 24 * 3600 + 10 * 60,
        arrivalSecs: 25 * 3600 + 30 * 60,
        durationSecs: 4800,
        legs: [{ kind: "transit", mode: "rail", routeName: "遅すぎる線" }],
      },
    ],
  }, { anchorType: "arrival", anchorSecs: 25 * 3600 });

  assert.equal(r.anchorType, "arrival");
  assert.equal(r.serviceDate, "20260809");
  assert.equal(r.anchorAt, "2026-08-09T16:00:00.000Z"); // 25:00 JST, next UTC day
  assert.equal(r.departureAt, "2026-08-09T14:20:00.000Z");
  assert.equal(r.arrivalAt, "2026-08-09T15:30:00.000Z"); // 24:30 JST, next UTC day
  assert.equal(r.durationSeconds, 4500); // journey duration + access walk; egress is in arrivalSecs
  assert.equal(r.accessWalkSeconds, 300);
  assert.equal(r.egressWalkSeconds, 120);
  assert.deepEqual(r.fare, { currency: "JPY", ticket: 220, ic: 216 });
  assert.equal(r.steps[0].service, "中央線");
  assert.equal(r.steps[0].trainType, "快速");
  assert.equal(r.steps[0].from.platform, "1番線");
  assert.equal(r.steps[0].to.platform, "3番線");
});

test("parseTransitPlan: departure anchor selects earliest viable arrival", () => {
  const r = parseTransitPlan({
    date: "20260810",
    timezone: "UTC",
    journeys: [
      { departureSecs: 7 * 3600 + 50 * 60, arrivalSecs: 8 * 3600 + 20 * 60, durationSecs: 1800, legs: [{ mode: "rail" }] },
      { departureSecs: 8 * 3600 + 5 * 60, arrivalSecs: 9 * 3600, durationSecs: 3300, legs: [{ mode: "rail", routeName: "遅い便" }] },
      { departureSecs: 8 * 3600 + 10 * 60, arrivalSecs: 8 * 3600 + 40 * 60, durationSecs: 1800, legs: [{ mode: "rail", routeName: "早い便" }] },
    ],
  }, { anchorType: "departure", anchorSecs: 8 * 3600 });

  assert.equal(r.anchorType, "departure");
  assert.equal(r.anchorAt, "2026-08-10T08:00:00.000Z");
  assert.equal(r.departureAt, "2026-08-10T08:10:00.000Z");
  assert.equal(r.arrivalAt, "2026-08-10T08:40:00.000Z");
  assert.equal(r.steps[0].service, "早い便");
});

test("parseTransitPlan: preserves rail, bus, and walking leg facts", () => {
  const r = parseTransitPlan({
    date: "20260810",
    timezone: "UTC",
    journeys: [{
      departureSecs: 8 * 3600,
      arrivalSecs: 9 * 3600,
      durationSecs: 3600,
      transferCount: 1,
      legs: [
        {
          kind: "walk", mode: "walk", from: { name: "自宅" }, to: { name: "東京駅" },
          departureSecs: 8 * 3600, arrivalSecs: 8 * 3600 + 10 * 60,
        },
        {
          kind: "transit", mode: "rail", routeName: "山手線", trainType: "普通", headsign: "渋谷",
          from: { name: "東京", platformCode: "2番線" }, to: { name: "品川", platformCode: "1番線" },
          departureSecs: 8 * 3600 + 12 * 60, arrivalSecs: 8 * 3600 + 30 * 60,
        },
        {
          kind: "transit", mode: "bus", routeName: "都営バス", headsign: "港南口",
          from: { name: "品川駅" }, to: { name: "港南口" },
          departureSecs: 8 * 3600 + 35 * 60, arrivalSecs: 9 * 3600,
        },
      ],
    }],
  });

  assert.equal(r.steps.length, 3);
  assert.equal(r.steps[0].kind, "walk");
  assert.equal(r.steps[0].mode, "walk");
  assert.equal(r.steps[0].from.name, "自宅");
  assert.equal(r.steps[0].to.name, "東京駅");
  assert.equal(r.steps[1].mode, "rail");
  assert.equal(r.steps[1].service, "山手線");
  assert.equal(r.steps[1].trainType, "普通");
  assert.equal(r.steps[1].headsign, "渋谷");
  assert.equal(r.steps[1].departAt, "2026-08-10T08:12:00.000Z");
  assert.equal(r.steps[1].arriveAt, "2026-08-10T08:30:00.000Z");
  assert.equal(r.steps[2].mode, "bus");
  assert.equal(r.steps[2].service, "都営バス");
  assert.equal(r.steps[2].from.platform, null);
  assert.equal(r.steps[2].to.platform, null);
  assert.equal(r.availability.platform, true);
  assert.equal(r.availability.stationExit, false);
});

test("parseTransitPlan: absent fare/platform/exit facts stay nullable and ungenerated", () => {
  const r = parseTransitPlan({
    date: "20260810",
    timezone: "UTC",
    journeys: [{
      departureSecs: 10, arrivalSecs: 20, durationSecs: 10,
      legs: [{ kind: "transit", mode: "rail", from: { name: "A" }, to: { name: "B" } }],
    }],
  });

  assert.equal(r.fare, null);
  assert.equal(r.steps[0].from.platform, null);
  assert.equal(r.steps[0].to.platform, null);
  assert.deepEqual(r.availability, { platform: false, fare: false, stationExit: false });
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[0], "stationExit"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[0], "bestCar"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(r.steps[0], "crowding"), false);
});

test("parseTransitPlan: missing or invalid timezone fails closed for anchored routes but keeps legacy duration", () => {
  const base = {
    date: "20260810",
    journeys: [{ departureSecs: 100, arrivalSecs: 300, durationSecs: 200, legs: [{ mode: "rail" }] }],
  };

  assert.equal(parseTransitPlan(base, { anchorType: "departure", anchorSecs: 100 }), null);
  assert.equal(parseTransitPlan({ ...base, timezone: "Not/AZone" }, { anchorType: "departure", anchorSecs: 100 }), null);
  const missingTimezoneLegacy = parseTransitPlan(base);
  const invalidTimezoneLegacy = parseTransitPlan({ ...base, timezone: "Not/AZone" });
  assert.equal(missingTimezoneLegacy.durationSecs, 200);
  assert.equal(invalidTimezoneLegacy.durationSecs, 200);
  assert.equal(missingTimezoneLegacy.timezone, null);
  assert.equal(invalidTimezoneLegacy.timezone, null);
  assert.equal(missingTimezoneLegacy.departureAt, null);
  assert.equal(invalidTimezoneLegacy.arrivalAt, null);
});

test("parseTransitPlan: invalid Gregorian service dates fail closed only when timestamps are required", () => {
  const base = {
    timezone: "UTC",
    journeys: [{ departureSecs: 100, arrivalSecs: 300, durationSecs: 200, legs: [{ mode: "rail" }] }],
  };

  for (const date of ["20260230", "20261301"]) {
    assert.equal(parseTransitPlan({ ...base, date }, { anchorType: "arrival", anchorSecs: 300 }), null);
    const legacy = parseTransitPlan({ ...base, date });
    assert.equal(legacy.durationSecs, 200);
    assert.equal(legacy.serviceDate, null);
    assert.equal(legacy.departureAt, null);
  }
});

test("parseTransitPlan: zero viable journeys for an anchor returns null", () => {
  const plan = {
    date: "20260810", timezone: "UTC",
    journeys: [
      { departureSecs: 100, arrivalSecs: 200, durationSecs: 100, legs: [{ mode: "rail" }] },
    ],
  };

  assert.equal(parseTransitPlan(plan, { anchorType: "arrival", anchorSecs: 150 }), null);
  assert.equal(parseTransitPlan(plan, { anchorType: "departure", anchorSecs: 250 }), null);
});
