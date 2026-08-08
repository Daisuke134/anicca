"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const adapters = require("./provider-cost-adapters.js");
const { routesDriveMinutes, legacyTransitMinutes, transitFetchPlan } = require("./travel.js");
const { geocodeAddress, clearGeocodeProcessMemo } = require("./geocode-cache.js");

function recorder() {
  const events = [];
  return {
    events,
    deps: {
      recordProviderCost: async (event) => {
        events.push(event);
        return true;
      },
    },
  };
}

test("Google geocoding and Routes operations record unknown actual billing without zero", async () => {
  const r = recorder();
  await adapters.recordGoogleGeocoding({ uid: "u1", requestId: "geo-1" }, r.deps);
  await adapters.recordGoogleRoutes({ uid: "u1", requestId: "route-1" }, r.deps);
  assert.equal(r.events.length, 2);
  assert.deepEqual(r.events.map((event) => [event.provider, event.operation]), [
    ["google", "geocoding"], ["google", "routes"],
  ]);
  for (const event of r.events) {
    assert.equal(event.actualStatus, "unknown");
    assert.equal(event.actualBilledUsd, null);
    assert.notEqual(event.estimatedUsd, 0);
  }
});

test("Transit operations preserve the provider operation and unknown billing state", async () => {
  const r = recorder();
  await adapters.recordTransitOperation({ uid: "u1", requestId: "transit-1", operation: "plan" }, r.deps);
  await adapters.recordTransitOperation({ uid: "u1", requestId: "transit-2", operation: "guidance" }, r.deps);
  assert.deepEqual(r.events.map((event) => event.operation), ["plan", "guidance"]);
  assert.ok(r.events.every((event) => event.provider === "transit" && event.actualStatus === "unknown"));
});

test("Composio records one real tool operation and never reports unknown as an estimated zero", async () => {
  const r = recorder();
  await adapters.recordComposioOperation({ uid: "u1", requestId: "composio-1", tool: "GOOGLECALENDAR_EVENTS_LIST" }, r.deps);
  assert.deepEqual(r.events[0], {
    uid: "u1", provider: "composio", sku: "GOOGLECALENDAR_EVENTS_LIST", operation: "tool_execute",
    requestId: "composio-1", quantity: 1, unit: "call", pricingVersion: "composio-2026-08",
    estimatedUsd: null, actualBilledUsd: null, actualStatus: "unknown",
    metadata: { tool: "GOOGLECALENDAR_EVENTS_LIST" },
  });
});

test("Gemini session records token metadata when supplied and otherwise uses a wall-time estimate", async () => {
  const withUsage = recorder();
  await adapters.recordGeminiSession({
    uid: "u1", requestId: "gemini-1", durationSeconds: 60,
    usageMetadata: { promptTokenCount: 10, responseTokenCount: 20 },
  }, withUsage.deps);
  assert.deepEqual(withUsage.events[0].metadata.usage, { promptTokenCount: 10, responseTokenCount: 20 });
  assert.equal(withUsage.events[0].actualStatus, "unknown");
  assert.ok(withUsage.events[0].estimatedUsd > 0);

  const withoutUsage = recorder();
  await adapters.recordGeminiSession({ uid: "u1", requestId: "gemini-2", durationSeconds: 0 }, withoutUsage.deps);
  assert.equal(withoutUsage.events[0].estimatedUsd, null);
  assert.equal(withoutUsage.events[0].actualBilledUsd, null);
  assert.equal(withoutUsage.events[0].actualStatus, "unknown");
});

test("Telnyx CDR records provider-measured actual cost", async () => {
  const r = recorder();
  await adapters.recordTelnyxCdr({
    uid: "u1", requestId: "cdr-1", durationSeconds: 90,
    cdr: { cost: { amount: "0.037", currency: "USD" }, call_control_id: "cc-1" },
  }, r.deps);
  assert.equal(r.events[0].provider, "telnyx");
  assert.equal(r.events[0].actualStatus, "measured");
  assert.equal(r.events[0].actualBilledUsd, 0.037);
  assert.equal(r.events[0].estimatedUsd, null);
});

test("Resend sends record recipient quantity and retain unknown billing", async () => {
  const r = recorder();
  await adapters.recordResendSend({ uid: "u1", requestId: "mail-1", recipientCount: 2, responseId: "re-1" }, r.deps);
  assert.equal(r.events[0].provider, "resend");
  assert.equal(r.events[0].quantity, 2);
  assert.equal(r.events[0].unit, "recipient");
  assert.equal(r.events[0].actualStatus, "unknown");
  assert.equal(r.events[0].actualBilledUsd, null);
});

test("Railway and Supabase allocations are measured when imported and unknown when absent", async () => {
  const r = recorder();
  await adapters.recordRailwayAllocation({ uid: "u1", requestId: "rail-1", amountUsd: "1.25", period: "2026-08-08" }, r.deps);
  await adapters.recordSupabaseAllocation({ uid: "u1", requestId: "supa-1", period: "2026-08-08" }, r.deps);
  assert.equal(r.events[0].provider, "railway");
  assert.equal(r.events[0].actualStatus, "measured");
  assert.equal(r.events[0].actualBilledUsd, 1.25);
  assert.equal(r.events[1].provider, "supabase");
  assert.equal(r.events[1].actualStatus, "unknown");
  assert.equal(r.events[1].actualBilledUsd, null);
  assert.equal(r.events[1].estimatedUsd, null);
});

test("a failed adapter write returns the recorder result and does not synthesize a zero", async () => {
  const seen = [];
  const ok = await adapters.recordGoogleRoutes({ uid: "u1", requestId: "route-fail" }, {
    recordProviderCost: async (event) => { seen.push(event); return false; },
  });
  assert.equal(ok, false);
  assert.equal(seen[0].actualBilledUsd, null);
  assert.notEqual(seen[0].estimatedUsd, 0);
});

test("route providers record each attempted Google operation and transit plan/guidance", async () => {
  const r = recorder();
  const original = global.fetch;
  const urls = [];
  global.fetch = async (url) => {
    urls.push(String(url));
    if (String(url).includes("routes.googleapis.com")) {
      return { ok: true, json: async () => ({ routes: [{ duration: "120s" }] }) };
    }
    if (String(url).includes("maps.googleapis.com")) {
      return { ok: true, json: async () => ({ status: "OK", routes: [{ legs: [{ duration: { value: 180 } }] }] }) };
    }
    return { ok: true, json: async () => ({ durationSecs: 120 }) };
  };
  try {
    await routesDriveMinutes("a", "b", "k", Date.now() + 60000, Date.now(), { uid: "u1", requestId: "google-route", recordProviderCost: r.deps.recordProviderCost });
    await legacyTransitMinutes("a", "b", "k", Date.now() + 60000, Date.now(), null, { uid: "u1", requestId: "google-transit", recordProviderCost: r.deps.recordProviderCost });
    await transitFetchPlan({ lat: 35.6, lon: 139.7 }, { lat: 35.7, lon: 139.8 }, {
      eventAt: "2026-08-08T02:00:00.000Z", timezone: "UTC", uid: "u1",
      fetchImpl: async (url) => ({ ok: true, json: async () => ({ durationSecs: 120, url }) }),
      recordProviderCost: r.deps.recordProviderCost,
    });
  } finally { global.fetch = original; }
  assert.ok(urls.some((url) => url.includes("routes.googleapis.com")));
  assert.ok(urls.some((url) => url.includes("maps.googleapis.com")));
  assert.deepEqual(r.events.map((event) => [event.provider, event.operation]), [
    ["google", "routes"], ["google", "transit"], ["transit", "plan"], ["transit", "guidance"],
  ]);
});

test("a successful Google geocode miss records one operation while a cache hit records none", async () => {
  const r = recorder();
  clearGeocodeProcessMemo();
  const store = new Map();
  const cache = {
    get: async (key) => store.get(key) || null,
    put: async (key, value) => { store.set(key, value); return true; },
  };
  let googleCalls = 0;
  const fetchImpl = async () => {
    googleCalls += 1;
    return { ok: true, json: async () => ({ results: [{ geometry: { location: { lat: 35.6, lng: 139.7 } } }] }) };
  };
  await geocodeAddress("Unique Cost Guard Place", "maps", {
    store: cache, fetchImpl, recordProviderCost: r.deps.recordProviderCost, uid: "u1", requestId: "geo-unique",
  });
  clearGeocodeProcessMemo();
  await geocodeAddress("Unique Cost Guard Place", "maps", {
    store: cache, fetchImpl, recordProviderCost: r.deps.recordProviderCost, uid: "u1", requestId: "geo-unique-hit",
  });
  assert.equal(googleCalls, 1);
  assert.equal(r.events.length, 1);
  assert.equal(r.events[0].operation, "geocoding");
});
