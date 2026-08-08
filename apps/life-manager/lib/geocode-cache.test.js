"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const {
  normalizeGeocodeAddress,
  createSupabaseGeocodeStore,
  geocodeAddress,
} = require("./geocode-cache.js");
const { recordProviderCost } = require("./ledger.js");

const SUPA = { supaUrl: "https://supa.invalid", supaKey: "service-role-key" };

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function persistentFetch() {
  const rows = new Map();
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (init.method === "POST") {
      const body = JSON.parse(init.body);
      rows.set(body.address_key, body);
      return response([], 201);
    }
    const expression = url.searchParams.get("address_key") || "";
    const key = expression.startsWith("eq.") ? expression.slice(3) : expression;
    const row = rows.get(key);
    return response(row ? [row] : []);
  };
  return { fetchImpl, rows, calls };
}

test("normalizeGeocodeAddress collapses case, Unicode whitespace, and compatibility forms", () => {
  assert.equal(
    normalizeGeocodeAddress("  ＭＡＩＮ　  Street\n 12 "),
    "main street 12",
  );
  assert.equal(normalizeGeocodeAddress("main street 12"), "main street 12");
  assert.equal(normalizeGeocodeAddress(" \t\n "), "");
});

test("Supabase geocode store persists a successful result across store instances", async () => {
  const db = persistentFetch();
  const first = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  const second = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  const key = normalizeGeocodeAddress(" 1-2 MAIN STREET ");
  const value = {
    lat: 35.681236,
    lng: 139.767125,
    provider: "google_geocoding",
    resolvedAt: "2026-08-08T06:00:00.000Z",
  };

  assert.equal(await first.put(key, value), true);
  assert.deepEqual(await second.get("1-2 main\nstreet"), value);
  assert.equal(db.rows.size, 1);
  assert.equal(db.calls.filter((call) => call.init.method === "POST").length, 1);
});

test("geocodeAddress writes only a valid result and a second process avoids Google", async () => {
  const db = persistentFetch();
  let googleCalls = 0;
  const googleFetch = async () => {
    googleCalls += 1;
    return response({ results: [{ geometry: { location: { lat: 35.68, lng: 139.76 } } }] });
  };
  const first = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  const second = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });

  const firstResult = await geocodeAddress(" 1-2 MAIN STREET ", "maps-key", {
    store: first,
    fetchImpl: googleFetch,
    now: () => "2026-08-08T06:00:00.000Z",
  });
  const secondResult = await geocodeAddress("1-2 main\nstreet", "maps-key", {
    store: second,
    fetchImpl: googleFetch,
    now: () => "2026-08-08T06:01:00.000Z",
  });

  assert.equal(googleCalls, 1);
  assert.equal(firstResult.lat, 35.68);
  assert.equal(firstResult.lon, 139.76);
  assert.equal(secondResult.lat, 35.68);
  assert.equal(secondResult.lon, 139.76);
});

test("empty or failed Google responses remain misses and are never persisted", async () => {
  const db = persistentFetch();
  const store = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  let googleCalls = 0;
  const googleFetch = async () => {
    googleCalls += 1;
    return googleCalls === 1
      ? response({ results: [] })
      : response({ status: "REQUEST_DENIED", results: [] }, 403);
  };

  assert.equal(await geocodeAddress("empty place", "maps-key", { store, fetchImpl: googleFetch }), null);
  assert.equal(await geocodeAddress("empty place", "maps-key", { store, fetchImpl: googleFetch }), null);
  assert.equal(await geocodeAddress("failed place", "maps-key", { store, fetchImpl: googleFetch }), null);
  assert.equal(googleCalls, 3);
  assert.equal(db.rows.size, 0);
  assert.equal(db.calls.filter((call) => call.init.method === "POST").length, 0);
});

test("every attempted Google geocode is recorded once, including empty, HTTP failure, and thrown requests", async () => {
  const events = [];
  let calls = 0;
  const fetchImpl = async () => {
    calls += 1;
    if (calls === 1) return response({ results: [] });
    if (calls === 2) return response({ status: "REQUEST_DENIED", results: [] }, 403);
    throw new Error("network down");
  };
  const recordProviderCost = async (event) => { events.push(event); return true; };
  const common = { fetchImpl, recordProviderCost, uid: "u1", store: new Map() };
  assert.equal(await geocodeAddress("unique-empty-guard-place", "maps-key", common), null);
  assert.equal(await geocodeAddress("unique-http-guard-place", "maps-key", common), null);
  assert.equal(await geocodeAddress("unique-throw-guard-place", "maps-key", common), null);
  assert.equal(calls, 3);
  assert.equal(events.length, 3);
  assert.equal(new Set(events.map((event) => event.requestId)).size, 3);
  assert.ok(events.every((event) => event.actualStatus === "unknown" && event.actualBilledUsd === null));
  assert.ok(events.every((event) => event.estimatedUsd > 0 && event.costClassification === "estimated"));
});

test("an empty Google response persists a nonzero SKU estimate with nullable unknown actual billing", async () => {
  const ledgerWrites = [];
  const result = await geocodeAddress("persisted-empty-geocode-guard", "maps-key", {
    store: new Map(),
    fetchImpl: async (url, init = {}) => {
      if (init.method === "POST") {
        ledgerWrites.push(JSON.parse(init.body));
        return response([], 201);
      }
      return response({ results: [] });
    },
    recordProviderCost: (event) => recordProviderCost(event, {
      supaUrl: "https://db.example", supaKey: "service",
      fetchImpl: async (url, init = {}) => {
        ledgerWrites.push(JSON.parse(init.body));
        return response([], 201);
      },
    }),
  });
  assert.equal(result, null);
  assert.equal(ledgerWrites.length, 1);
  assert.ok(ledgerWrites[0].estimated_usd > 0);
  assert.equal(ledgerWrites[0].actual_billed_usd, null);
  assert.equal(ledgerWrites[0].actual_status, "unknown");
});

test("cache keys carry no tenant identity or caller-controlled query fragments", async () => {
  const db = persistentFetch();
  const store = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  await store.get("Tenant A\n1 Main & Home");
  const request = db.calls[0];
  assert.equal(request.url.searchParams.get("address_key"), "eq.tenant a 1 main & home");
  assert.equal(request.url.searchParams.has("uid"), false);
});
