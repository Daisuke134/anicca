"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildAnchoredRouteRequest, computeMobileRoute, createStructuredRouteProviders, projectMobileRoute, routeAccepted } = require("../lib/mobile-route.js");
const { projectSemanticMessage } = require("../lib/mobile-localization.js");

const event = {
  id: "event-1", summary: "Meeting", location: "Roppongi", timezone: "America/Los_Angeles",
  startIso: "2026-11-01T09:00:00-08:00", endIso: "2026-11-01T10:00:00-08:00",
};

test("route requests preserve event timezone/date and use arrive-by outbound or depart-at return semantics", () => {
  const outbound = buildAnchoredRouteRequest({ event, origin: "Shibuya", direction: "outbound" });
  assert.equal(outbound.direction, "outbound");
  assert.equal(outbound.arriveBy, event.startIso);
  assert.equal(outbound.departAt, null);
  assert.equal(outbound.timezone, "America/Los_Angeles");
  const returned = buildAnchoredRouteRequest({ event, origin: "Roppongi", direction: "return" });
  assert.equal(returned.direction, "return");
  assert.equal(returned.arriveBy, null);
  assert.equal(returned.departAt, event.endIso);
  assert.equal(returned.eventDate, "2026-11-01");
});

test("accepted Transit result prevents Google fallback; provider failure falls back once", async () => {
  let transitCalls = 0;
  let googleCalls = 0;
  const raw = { status: "route_ready", provider: "transit", eventId: "event-1", timezone: event.timezone, origin: { displayNames: { en: "Shibuya", ja: "渋谷" } }, destination: { displayNames: { en: "Roppongi", ja: "六本木" } }, leaveAt: "2026-11-01T16:00:00.000Z", arriveAt: "2026-11-01T16:27:00.000Z", durationSeconds: 1620, bufferSeconds: 180, transferCount: 0, fare: null, geometry: null, steps: [] };
  const deps = {
    transitProvider: async (request) => { transitCalls++; assert.equal(request.arriveBy, event.startIso); return raw; },
    googleProvider: async () => { googleCalls++; return { ...raw, provider: "google" }; },
  };
  const result = await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", deps);
  assert.equal(result.provider, "transit");
  assert.equal(transitCalls, 1);
  assert.equal(googleCalls, 0);
  const fallback = await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", { transitProvider: async () => null, googleProvider: async (request) => { assert.equal(request.arriveBy, event.startIso); return { ...raw, provider: "google" }; } });
  assert.equal(fallback.provider, "google");
});

test("route projection keeps provider facts, nullable values, and omits unsupported precision", () => {
  const value = projectMobileRoute({
    status: "route_ready", provider: "transit", providerAttribution: "Transit API", computedAt: "2026-08-08T00:00:00.000Z", timezone: "Asia/Tokyo", eventId: "event-1",
    origin: { displayNames: { en: "Shibuya", ja: "渋谷" }, userContent: "自宅" }, destination: { displayNames: { en: "Roppongi", ja: "六本木" }, userContent: "六本木" },
    leaveAt: "2026-08-08T01:00:00.000Z", arriveAt: "2026-08-08T01:27:00.000Z", durationSeconds: 1620, bufferSeconds: 180, transferCount: 1,
    fare: null, geometry: null, steps: [{ sequence: 1, mode: "train", instruction: { en: "Take the line", ja: "線に乗る" }, from: { en: "Shibuya", ja: "渋谷" }, to: { en: "Roppongi", ja: "六本木" }, service: { en: "Toei Oedo Line", ja: "都営大江戸線" }, headsign: null, platform: null, departAt: null, arriveAt: null, durationSeconds: 900, entrance: "guess" }], entrance: "guess",
  }, "en");
  assert.equal(value.origin.displayName, "Shibuya");
  assert.equal(value.steps[0].service, "Toei Oedo Line");
  assert.equal(value.steps[0].platform, null);
  assert.equal(Object.hasOwn(value, "entrance"), false);
  assert.equal(Object.hasOwn(value.steps[0], "entrance"), false);
});

test("outbound anchors use the event local date and reject malformed provider success", () => {
  const overnight = buildAnchoredRouteRequest({
    event: { id: "overnight", location: "Destination", startIso: "2026-11-01T00:30:00.000Z", timezone: "America/Los_Angeles" },
    origin: "Origin",
  });
  assert.equal(overnight.eventDate, "2026-10-31");
  assert.equal(overnight.arriveBy, "2026-11-01T00:30:00.000Z");
  assert.equal(routeAccepted({ provider: "transit" }), false);
  assert.equal(routeAccepted({ status: "route_ready" }), false);
  assert.throws(() => buildAnchoredRouteRequest({
    event: { id: "return-without-end", location: "Destination", startIso: "2026-11-01T00:30:00.000Z", timezone: "UTC" },
    origin: "Origin", direction: "return",
  }), (error) => error.code === "route_anchor_invalid");
  assert.throws(() => buildAnchoredRouteRequest({
    event: { id: "missing-destination", startIso: "2026-11-01T00:30:00.000Z", timezone: "UTC" },
    origin: "Origin",
  }), (error) => error.code === "missing_destination");
  assert.throws(() => buildAnchoredRouteRequest({
    event: { id: "unknown-zone", location: "Destination", startIso: "2026-11-01T00:30:00.000Z" },
    origin: "Origin",
  }), (error) => error.code === "route_timezone_required");
});

test("production structured providers reach route_ready through Transit and cache the anchored result", async () => {
  const calls = [];
  const providers = createStructuredRouteProviders({
    mapsKey: "maps-test-key",
    cacheStore: new Map(),
    fetchImpl: async (url) => {
      calls.push(String(url));
      if (String(url).includes("geocode")) {
        return { ok: true, json: async () => ({ status: "OK", results: [{ geometry: { location: { lat: 35.681, lng: 139.767 } } }] }) };
      }
      return { ok: true, json: async () => ({ journeys: [{ arrivalSecs: 1_029, durationSecs: 1_029, accessWalkSecs: 61, transferCount: 1, legs: [{ mode: "rail", routeName: "中央線快速" }] }] }) };
    },
  });
  const first = await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", providers);
  const second = await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", providers);
  assert.equal(first.status, "route_ready");
  assert.equal(first.provider, "transit");
  assert.equal(first.timezone, event.timezone);
  assert.equal(first.arriveAt, new Date(event.startIso).toISOString());
  assert.equal(second.provider, "transit");
  assert.equal(calls.filter((url) => url.includes("transit.ls8h.com")).length, 1);
  assert.equal(calls.some((url) => url.includes("directions")), false);
});

test("router-shaped production dependencies reuse the structured provider cache", async () => {
  let transitCalls = 0;
  const providers = createStructuredRouteProviders({
    mapsKey: "maps-test-key",
    cacheStore: new Map(),
    fetchImpl: async (url) => {
      if (String(url).includes("geocode")) {
        return { ok: true, json: async () => ({ status: "OK", results: [{ geometry: { location: { lat: 35.681, lng: 139.767 } } }] }) };
      }
      transitCalls++;
      return { ok: true, json: async () => ({ journeys: [{ arrivalSecs: 1_029, durationSecs: 1_029, legs: [{ mode: "rail", routeName: "Chuo Line" }] }] }) };
    },
  });
  const runtime = { routeProviders: providers };
  await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", runtime);
  await computeMobileRoute({ uid: "user-a" }, event, "Shibuya", runtime);
  assert.equal(transitCalls, 1);
});

test("route projection preserves access, egress, freshness, and explicit nullable attribution", () => {
  const value = projectMobileRoute({
    status: "route_ready", provider: "transit", providerAttribution: null,
    accessWalkSeconds: 120, egressWalkSeconds: null,
    freshness: { source: "provider", computedAt: "2026-08-08T00:00:00.000Z" },
    eventId: "event-1", timezone: "UTC",
    origin: { displayNames: { en: "Origin", ja: "出発" } },
    destination: { displayNames: { en: "Destination", ja: "目的地" } },
    steps: [],
  }, "en");
  assert.equal(value.accessWalkSeconds, 120);
  assert.equal(value.egressWalkSeconds, null);
  assert.deepEqual(value.freshness, { source: "provider", computedAt: "2026-08-08T00:00:00.000Z" });
  assert.equal(value.providerAttribution, null);
});

test("route projection leaves absent provider facts null instead of manufacturing defaults", () => {
  const value = projectMobileRoute({
    status: "route_ready", provider: "transit", eventId: "event-1", timezone: "UTC",
    origin: { displayNames: { en: "Origin", ja: "出発" } },
    destination: { displayNames: { en: "Destination", ja: "目的地" } }, steps: [],
  }, "en");
  assert.equal(value.computedAt, null);
  assert.equal(value.durationSeconds, null);
  assert.equal(value.bufferSeconds, null);
  assert.equal(value.transferCount, null);
});

test("route chat projection refuses an unknown Calendar timezone instead of formatting in UTC", () => {
  assert.throws(() => projectSemanticMessage({
    id: "message:v1:unknown-zone", cursor: "cursor:v1:unknown-zone", createdAt: "2026-08-08T00:00:00.000Z",
    key: "chat.route_ready", route: { status: "route_ready", provider: "transit", leaveAt: "2026-08-08T01:00:00.000Z", bufferSeconds: 180 },
  }, "en"), (error) => error.code === "route_timezone_required");
});
