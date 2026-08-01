"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createConnectorRouteMinutes } = require("./connector-route-minutes.js");

test("Connector route delegates inbound and outbound anchors to the existing Life Manager router", async () => {
  const calls = [];
  const routeMinutes = createConnectorRouteMinutes({
    mapsKey: "maps-key-ref-value",
    homeRef: "home://dais-local",
    homeLocation: "東京駅",
    now: () => 1_800_000_000_000,
    async directionsMinutes(...args) { calls.push(args); return 27; },
  });
  assert.equal(await routeMinutes({
    direction: "inbound", from: "home://dais-local", to: "渋谷駅", anchor_at: "2026-08-05T12:00:00+09:00",
  }), 27);
  assert.equal(await routeMinutes({
    direction: "outbound", from: "渋谷駅", to: "東京駅", anchor_at: "2026-08-05T13:00:00+09:00",
  }), 27);
  assert.deepEqual(calls.map((call) => ({
    from: call[0], to: call[1], key: call[2], anchor: call[3], now: call[4], departure: call[5],
  })), [
    { from: "東京駅", to: "渋谷駅", key: "maps-key-ref-value", anchor: Date.parse("2026-08-05T12:00:00+09:00"), now: 1_800_000_000_000, departure: false },
    { from: "渋谷駅", to: "東京駅", key: "maps-key-ref-value", anchor: Date.parse("2026-08-05T13:00:00+09:00"), now: 1_800_000_000_000, departure: true },
  ]);
});

test("Connector route fails closed for missing key, malformed contract, or unavailable duration", async () => {
  assert.throws(() => createConnectorRouteMinutes({ mapsKey: "" }), /route unavailable/i);
  const routeMinutes = createConnectorRouteMinutes({
    mapsKey: "key",
    async directionsMinutes() { return null; },
  });
  await assert.rejects(routeMinutes({
    direction: "sideways", from: "A", to: "B", anchor_at: "2026-08-05T12:00:00+09:00",
  }), /route invalid/i);
  await assert.rejects(routeMinutes({
    direction: "inbound", from: "A", to: "B", anchor_at: "bad",
  }), /route invalid/i);
  await assert.rejects(routeMinutes({
    direction: "inbound", from: "A", to: "B", anchor_at: "2026-08-05T12:00:00+09:00",
  }), /route unavailable/i);
  const unresolvedHome = createConnectorRouteMinutes({
    mapsKey: "key",
    homeRef: "home://dais-local",
    async directionsMinutes() { return 1; },
  });
  await assert.rejects(unresolvedHome({
    direction: "inbound", from: "home://dais-local", to: "B", anchor_at: "2026-08-05T12:00:00+09:00",
  }), /route unavailable/i);
});
