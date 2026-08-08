"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { directionsRoute } = require("../lib/travel.js");
const { makeRouteCache } = require("../lib/route-cache.js");
const { geocodeAddress } = require("../lib/geocode-cache.js");
const { makeComposioCalendar } = require("../lib/transport/calendar-composio.js");
const { placeCall } = require("../lib/dial.js");

test("Google fallback is budget-authorized and does not call the paid provider after denial", async () => {
  let googleCalls = 0;
  const route = await directionsRoute("origin", "destination", "maps", Date.now() + 60000, Date.now(), false, {
    _geocode: async (address) => address === "origin" ? { lat: 35.6, lon: 139.7 } : { lat: 35.7, lon: 139.8 },
    _transitFetch: async () => null,
    _directionsMinutesGoogle: async () => { googleCalls += 1; return 30; },
    _authorizeProviderOperation: async (input) => {
      assert.equal(input.provider, "google");
      assert.equal(input.operation, "fallback");
      return { allowed: false, reason: "paid_fallback_disabled" };
    },
    _routeCache: makeRouteCache({ store: new Map() }),
  });
  assert.equal(route, null);
  assert.equal(googleCalls, 0);
});

test("a Google geocode miss is budget-authorized before the paid request", async () => {
  let googleCalls = 0;
  const result = await geocodeAddress("unresolved", "maps", {
    store: { get: async () => null, put: async () => true },
    fetchImpl: async () => { googleCalls += 1; return { ok: true, json: async () => ({ results: [] }) }; },
    authorizeProviderOperation: async (input) => {
      assert.equal(input.provider, "google");
      assert.equal(input.operation, "geocoding");
      return { allowed: false, reason: "budget_stopped" };
    },
  });
  assert.equal(result, null);
  assert.equal(googleCalls, 0);
});

test("nonessential Composio refresh checks the shared budget before the tool request", async () => {
  let providerCalls = 0;
  const calendar = makeComposioCalendar({
    apiKey: "k",
    fetchImpl: async () => { providerCalls += 1; return { ok: true, json: async () => ({ successful: true, data: { items: [] } }) }; },
    authorizeProviderOperation: async (input) => {
      assert.equal(input.provider, "composio");
      assert.equal(input.essential, false);
      return { allowed: false, reason: "budget_stopped" };
    },
  });
  assert.deepEqual(await calendar.listEventsRaw("u1", {}), []);
  assert.equal(providerCalls, 0);
});

test("new Telnyx calls consult the shared voice cap before dialing", async () => {
  const before = {
    TELNYX_API_KEY: process.env.TELNYX_API_KEY,
    TELNYX_CONNECTION_ID: process.env.TELNYX_CONNECTION_ID,
    TELNYX_PHONE_NUMBER: process.env.TELNYX_PHONE_NUMBER,
  };
  process.env.TELNYX_API_KEY = "k";
  process.env.TELNYX_CONNECTION_ID = "connection";
  process.env.TELNYX_PHONE_NUMBER = "+10000000000";
  try {
    const result = await placeCall({
      to: "+10000000001", streamUrl: "wss://example.test/ws", uid: "u1",
      authorizeProviderOperation: async (input) => {
        assert.equal(input.provider, "telnyx");
        assert.equal(input.operation, "call_session");
        return { allowed: false, reason: "voice_user_cap" };
      },
    });
    assert.equal(result.ok, false);
    assert.match(result.error, /voice_user_cap/);
  } finally {
    for (const [key, value] of Object.entries(before)) {
      if (value == null) delete process.env[key];
      else process.env[key] = value;
    }
  }
});
