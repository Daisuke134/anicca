"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertGeneratedEnglish,
  assertIso,
  assertNoClientAuthority,
} = require("./mobile-contract-support.js");

const UNSUPPORTED_ROUTE_KEYS = new Set(["entrance", "exit", "optimalCar", "crowding"]);

test("structured route preserves event anchor, provider facts, and ordered legs", () => {
  const route = fixture("route.json");
  assert.deepEqual(Object.keys(route).sort(), [
    "arriveAt", "bufferSeconds", "computedAt", "destination", "durationSeconds", "eventId",
    "fare", "geometry", "leaveAt", "origin", "provider", "providerAttribution", "status",
    "steps", "timezone", "transferCount",
  ].sort());
  assert.equal(route.status, "route_ready");
  assert.equal(route.provider, "transit");
  assert.equal(typeof route.providerAttribution, "string");
  assert.equal(typeof route.timezone, "string");
  assertIso(route.computedAt, "route computedAt");
  assertIso(route.leaveAt, "route leaveAt");
  assertIso(route.arriveAt, "route arriveAt");
  assert.equal(route.durationSeconds > 0, true);
  assert.equal(route.bufferSeconds >= 0, true);
  assert.equal(route.transferCount >= 0, true);
  assert.equal(typeof route.eventId, "string");
  assert.equal(typeof route.origin.displayName, "string");
  assert.equal(typeof route.destination.displayName, "string");
  assert.equal(route.geometry, null);
  assert.equal(route.fare.currency, "JPY");
  assert.equal(typeof route.fare.amount, "number");
  assert.equal(typeof route.fare.medium, "string");

  assert.equal(Array.isArray(route.steps), true);
  assert.equal(route.steps.length > 0, true);
  route.steps.forEach((step, index) => {
    assert.equal(step.sequence, index + 1);
    assert.equal(typeof step.mode, "string");
    assert.equal(typeof step.instruction, "string");
    assertIso(step.departAt, `route step ${step.sequence} departAt`);
    assertIso(step.arriveAt, `route step ${step.sequence} arriveAt`);
    assert.equal(step.durationSeconds > 0, true);
    for (const key of UNSUPPORTED_ROUTE_KEYS) assert.equal(Object.hasOwn(step, key), false);
  });
  assertGeneratedEnglish(route, "structured route");
  assertNoClientAuthority(route, "structured route");
});

test("route fixture keeps nullable provider facts null instead of inventing precision", () => {
  const route = fixture("route.json");
  const nullableStep = route.steps.find((step) => step.platform === null && step.service === null);
  assert.ok(nullableStep, "fixture must demonstrate nullable provider facts");
  assert.equal(route.geometry, null);
  assert.equal(Object.hasOwn(route, "entrance"), false);
  assert.equal(Object.hasOwn(route, "exit"), false);
  assert.equal(Object.hasOwn(route, "optimalCar"), false);
  assert.equal(Object.hasOwn(route, "crowding"), false);
  assert.equal(route.origin.displayName, "Shipathon Roppongi");
  assert.equal(route.destination.displayName, "Tokyo Tower");
  assert.equal(Object.hasOwn(route.origin, "coordinates"), false);
  assert.equal(Object.hasOwn(route.destination, "coordinates"), false);
});
