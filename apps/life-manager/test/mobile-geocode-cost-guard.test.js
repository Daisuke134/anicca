"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const travel = require("../lib/travel.js");
const { createSupabaseGeocodeStore } = require("../lib/geocode-cache.js");
const { makeRouteCache } = require("../lib/route-cache.js");

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

test("row 9: repeated normalized addresses make zero new Google geocode requests", async () => {
  const db = persistentFetch();
  const firstStore = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  const secondStore = createSupabaseGeocodeStore({ ...SUPA, fetchImpl: db.fetchImpl });
  let googleCalls = 0;
  const googleFetch = async () => {
    googleCalls += 1;
    return response({ results: [{ geometry: { location: { lat: 35.681, lng: 139.767 } } }] });
  };
  const transitFetch = async () => ({
    journeys: [{ durationSecs: 900, arrivalSecs: 900, departureSecs: 0, legs: [] }],
  });
  const at = Date.parse("2026-08-09T09:00:00+09:00");
  const options = (store) => ({
    _geocodeStore: store,
    _fetchImpl: googleFetch,
    _transitFetch: transitFetch,
    _directionsMinutesGoogle: async () => 45,
    _routeCache: makeRouteCache({ store: new Map(), ttlMs: 600000 }),
  });

  await travel.directionsMinutes(" 1-2 MAIN STREET ", " 3-4 SHIBUYA\nTOKYO ", "maps-key", at, at - 60000, false, options(firstStore));
  await travel.directionsMinutes("1-2 main street", "3-4 shibuya tokyo", "maps-key", at, at - 60000, false, options(secondStore));

  assert.equal(googleCalls, 2, "one request per unique address, none on the second process instance");
  assert.equal(db.rows.size, 2);
});
