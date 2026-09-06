"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { directionsRoute, geocodeAddress } = require("./travel.js");
const { makeRouteCache } = require("./route-cache.js");

test("Google Directions success and later cache hit emit separate usage facts", async () => {
  const events = [];
  const cache = makeRouteCache({ store: new Map(), ttlMs: 600000, now: () => 1000 });
  const oldFetch = globalThis.fetch;
  let providerCalls = 0;
  globalThis.fetch = async () => {
    providerCalls += 1;
    return { ok: true, status: 200, json: async () => ({
      status: "OK", routes: [{ legs: [{ duration: { value: 900 } }] }],
    }) };
  };
  const opts = {
    uid: "tenant-1", _routeCache: cache,
    _recordUsageEvent: async (event) => { events.push(event); return true; },
  };
  try {
    await directionsRoute("geo:40.730,-73.930", "geo:40.740,-73.980", "key", 2000000, 1000, false, opts);
    await directionsRoute("geo:40.730,-73.930", "geo:40.740,-73.980", "key", 2000000, 1000, false, opts);
    await directionsRoute("geo:40.730,-73.930", "geo:40.740,-73.980", "key", 2000000, 1000, false, opts);
  } finally {
    globalThis.fetch = oldFetch;
  }
  assert.equal(providerCalls, 1);
  assert.deepEqual(events.map((event) => ({
    provider: event.provider, feature: event.feature, outcome: event.outcome,
    units: event.providerUnits, cost: event.estimatedCostUsd,
  })), [
    { provider: "google_maps", feature: "directions", outcome: "success", units: 1, cost: 0.005 },
    { provider: "google_maps", feature: "travel_route", outcome: "cache_hit", units: 0, cost: 0 },
  ]);
});

test("Google Directions 4xx response is recorded as paid failure work", async () => {
  const events = [];
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 400, json: async () => ({ status: "INVALID_REQUEST" }) });
  try {
    const route = await directionsRoute(
      "geo:40.730,-73.930", "geo:40.740,-73.980", "key", 2000000, 1000, false,
      { uid: "tenant-1", _routeCache: makeRouteCache({ store: new Map(), now: () => 1000 }),
        _recordUsageEvent: async (event) => { events.push(event); return true; } },
    );
    assert.equal(route, null);
  } finally {
    globalThis.fetch = oldFetch;
  }
  assert.equal(events.length, 1);
  assert.equal(events[0].outcome, "failure");
  assert.equal(events[0].failureClass, "provider_4xx");
  assert.equal(events[0].providerUnits, 1);
  assert.equal(events[0].estimatedCostUsd, 0.005);
});

test("Geocoding 4xx is not replayed during negative TTL and a later valid response recovers", async () => {
  const oldFetch = globalThis.fetch;
  const oldNow = Date.now;
  let now = 1_000, calls = 0;
  Date.now = () => now;
  globalThis.fetch = async () => {
    calls += 1;
    if (calls === 1) return { ok: false, status: 400, json: async () => ({ status: "INVALID_REQUEST" }) };
    return { ok: true, status: 200, json: async () => ({ status: "OK", results: [{
      geometry: { location: { lat: 35.68, lng: 139.76 } },
    }] }) };
  };
  const usage = { tenantId: "tenant-geocode", options: { _recordUsageEvent: async () => true } };
  try {
    assert.equal(await geocodeAddress("COST-02 unique address", "key", usage), null);
    assert.equal(await geocodeAddress("COST-02 unique address", "key", usage), null);
    assert.equal(calls, 1);
    now += 30 * 60_000 + 1;
    assert.deepEqual(await geocodeAddress("COST-02 unique address", "key", usage), {
      lat: 35.68, lon: 139.76,
    });
    assert.equal(calls, 2);
  } finally {
    Date.now = oldNow;
    globalThis.fetch = oldFetch;
  }
});
