// travel-routes.test.js — #71 Routes API migration: pure helpers for the traffic-aware DRIVE leg.
// Run: node --test apps/life-call/lib/travel-routes.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { parseDurationSeconds, minutesFromSeconds, buildDriveBody, clampDepartIso } = require("./travel.js");

test('parseDurationSeconds("812s") → 812', () => {
  assert.equal(parseDurationSeconds("812s"), 812);
});
test('parseDurationSeconds("1002s") → 1002', () => {
  assert.equal(parseDurationSeconds("1002s"), 1002);
});
test("parseDurationSeconds garbage / missing → null", () => {
  assert.equal(parseDurationSeconds(""), null);
  assert.equal(parseDurationSeconds(undefined), null);
  assert.equal(parseDurationSeconds("abc"), null);
  assert.equal(parseDurationSeconds(null), null);
});

test("minutesFromSeconds floors at 5 min", () => {
  assert.equal(minutesFromSeconds(60), 5);    // 1 min raw → floored to 5
  assert.equal(minutesFromSeconds(0), 5);
});
test("minutesFromSeconds rounds 812s → 14", () => {
  assert.equal(minutesFromSeconds(812), 14);
});
test("minutesFromSeconds rounds 1002s → 17", () => {
  assert.equal(minutesFromSeconds(1002), 17);
});
test("minutesFromSeconds NO ×1.4 fudge (1200s → 20, not 28)", () => {
  assert.equal(minutesFromSeconds(1200), 20);
});

test("buildDriveBody sets DRIVE + TRAFFIC_AWARE_OPTIMAL + departureTime", () => {
  const b = buildDriveBody("新宿区南元町15-27", "東京駅", "2026-06-21T05:00:00Z");
  assert.equal(b.travelMode, "DRIVE");
  assert.equal(b.routingPreference, "TRAFFIC_AWARE_OPTIMAL");
  assert.equal(b.departureTime, "2026-06-21T05:00:00Z");
  assert.equal(b.origin.address, "新宿区南元町15-27");
  assert.equal(b.destination.address, "東京駅");
});

test("clampDepartIso: future depart kept as-is (ISO, no ms)", () => {
  const now = Date.parse("2026-06-21T00:00:00Z");
  const depart = Date.parse("2026-06-21T05:00:00Z");
  assert.equal(clampDepartIso(depart, now), "2026-06-21T05:00:00Z");
});
test("clampDepartIso: past depart bumped to now+60s (Routes rejects past departureTime)", () => {
  const now = Date.parse("2026-06-21T00:00:00Z");
  const past = Date.parse("2026-06-20T00:00:00Z");
  assert.equal(clampDepartIso(past, now), "2026-06-21T00:01:00Z");
});
