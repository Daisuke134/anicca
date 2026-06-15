// travel-handler.test.js — integration tests for life-travel Netlify handler.
//
// Covers the gaps identified by the adversarial verifier (2026-06-16):
//   1. The handler must return 200 (not 500) when auth succeeds
//   2. The handler must call GCal insert for events missing travel blocks
//   3. The Maps Directions API must be called when a destination is set
//   4. Token refresh flow (GOOGLE_REFRESH_TOKEN path) must work
//   5. Chained events (multiple events needing travel blocks) all get blocks
//
// Uses node:test + node:assert. Mocks `fetch` globally per test.
// Pattern mirrors handler-telemetry.test.js (proven template).
// node --test netlify/functions/_lib/__tests__/travel-handler.test.js

const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const path = require("path");

// ── Helpers ──────────────────────────────────────────────────────────────────

// Build a minimal GCal event object (timed event)
function makeEvent(id, summary, dateTime, location = null) {
  return {
    id,
    summary,
    start: { dateTime },
    end: { dateTime: new Date(new Date(dateTime).getTime() + 3600000).toISOString() },
    ...(location ? { location } : {}),
  };
}

// Build a mock GCal events list response
function gcalListResponse(events) {
  return { items: events };
}

// Build a mock GCal insert response (minimal event resource)
function gcalInsertResponse(summary, startDt) {
  return { id: `mock-${summary.slice(0, 8)}-${Date.now()}`, summary, start: { dateTime: startDt } };
}

// Build a mock Maps Directions API response
function mapsDirectionsResponse(durationSec) {
  return {
    routes: [{ legs: [{ duration: { value: durationSec } }] }],
  };
}

// ── Per-test env + fetch isolation ───────────────────────────────────────────

let originalFetch;
let originalEnv;

// Safe cache eviction — won't throw if module was never loaded
function clearCache(...ids) {
  for (const id of ids) {
    try { delete require.cache[require.resolve(id)]; } catch (_) {}
  }
}

beforeEach(() => {
  originalFetch = globalThis.fetch;
  originalEnv = { ...process.env };
  clearCache("../../life-travel", "../gcal-token", "../travel-logic");
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env = originalEnv;
  clearCache("../../life-travel", "../gcal-token", "../travel-logic");
});

// ── Test 1: 405 for non-POST ──────────────────────────────────────────────────

test("handler returns 405 for GET requests", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-test";
  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "GET" });
  assert.strictEqual(res.statusCode, 405);
});

// ── Test 2: 500 when no auth credentials are present ─────────────────────────

test("handler returns 500 when no auth credentials are configured", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  delete process.env.GOOGLE_REFRESH_TOKEN;
  delete process.env.GOOGLE_CLIENT_ID;
  delete process.env.GOOGLE_CLIENT_SECRET;

  globalThis.fetch = async () => {
    throw new Error("should not be called without auth");
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });
  assert.strictEqual(res.statusCode, 500);
  assert.ok(res.body.includes("missing"));
});

// ── Test 3: GOOGLE_CALENDAR_TOKEN path — returns 200, no insert needed ───────

test("handler returns 200 with no inserts when all events already have travel blocks", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  const events = [
    makeEvent("ev1", "歯科検診", "2026-06-17T10:00:00+09:00"),
    makeEvent("ev2", "[Travel] 歯科検診", "2026-06-17T09:40:00+09:00"),
  ];

  globalThis.fetch = async (url) => {
    if (url.includes("calendar/v3")) {
      return { ok: true, json: async () => gcalListResponse(events) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  const body = JSON.parse(res.body);
  assert.ok(body.ok);
  assert.strictEqual(body.inserted.length, 0);
  assert.strictEqual(body.checked, 2);
});

// ── Test 4: GCal insert is called for events missing travel blocks ────────────

test("handler inserts [Travel] block for event missing one (default 20min, no Maps key)", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  delete process.env.GOOGLE_MAPS_API_KEY; // no Maps key → 20min default

  const events = [
    makeEvent("ev1", "Team Sync", "2026-06-17T14:00:00+09:00"),
  ];

  const insertedBodies = [];

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method !== "POST")) {
      // list call
      return { ok: true, json: async () => gcalListResponse(events) };
    }
    if (url.includes("calendar/v3") && opts && opts.method === "POST") {
      // insert call
      const body = JSON.parse(opts.body);
      insertedBodies.push(body);
      return {
        ok: true,
        json: async () => gcalInsertResponse(body.summary, body.start.dateTime),
      };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  const resBody = JSON.parse(res.body);
  assert.strictEqual(resBody.inserted.length, 1);
  assert.strictEqual(resBody.inserted[0].for, "Team Sync");
  assert.strictEqual(resBody.inserted[0].durationMin, 20); // default fallback

  // Verify the inserted event has [Travel] prefix
  assert.strictEqual(insertedBodies.length, 1);
  assert.ok(insertedBodies[0].summary.startsWith("[Travel]"), "inserted event must have [Travel] prefix");
  assert.ok(insertedBodies[0].summary.includes("Team Sync"));
});

// ── Test 5: Google Maps Directions API is called when destination is set ──────

test("handler calls Maps API and uses real duration when event has location", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  process.env.GOOGLE_MAPS_API_KEY = "maps-key-test";

  const REAL_DURATION_SEC = 30 * 60; // 30 minutes from Maps

  const events = [
    makeEvent("ev1", "歯科検診", "2026-06-17T10:00:00+09:00", "信濃町駅"),
  ];

  let mapsWasCalled = false;
  let gcalInsertCalled = false;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("maps.googleapis.com")) {
      mapsWasCalled = true;
      assert.ok(url.includes("destination="), "Maps URL must include destination");
      assert.ok(url.includes("maps-key-test"), "Maps URL must include API key");
      return { ok: true, json: async () => mapsDirectionsResponse(REAL_DURATION_SEC) };
    }
    if (url.includes("calendar/v3") && (!opts || opts.method !== "POST")) {
      return { ok: true, json: async () => gcalListResponse(events) };
    }
    if (url.includes("calendar/v3") && opts && opts.method === "POST") {
      gcalInsertCalled = true;
      const body = JSON.parse(opts.body);
      return {
        ok: true,
        json: async () => gcalInsertResponse(body.summary, body.start.dateTime),
      };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  assert.ok(mapsWasCalled, "Maps Directions API must be called when event has location");
  assert.ok(gcalInsertCalled, "GCal insert must be called");

  const resBody = JSON.parse(res.body);
  assert.strictEqual(resBody.inserted.length, 1);
  assert.strictEqual(resBody.inserted[0].durationMin, 30); // from Maps (not 20min default)
});

// ── Test 6: Chained events — multiple events all get travel blocks ─────────────

test("handler inserts travel blocks for all chained events missing them", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";
  delete process.env.GOOGLE_MAPS_API_KEY;

  const events = [
    makeEvent("ev1", "Morning Meeting", "2026-06-17T09:00:00+09:00"),
    makeEvent("ev2", "Dentist", "2026-06-17T11:00:00+09:00"),
    makeEvent("ev3", "Lunch with Team", "2026-06-17T13:00:00+09:00"),
  ];

  const insertedSummaries = [];

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method !== "POST")) {
      return { ok: true, json: async () => gcalListResponse(events) };
    }
    if (url.includes("calendar/v3") && opts && opts.method === "POST") {
      const body = JSON.parse(opts.body);
      insertedSummaries.push(body.summary);
      return {
        ok: true,
        json: async () => gcalInsertResponse(body.summary, body.start.dateTime),
      };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  const resBody = JSON.parse(res.body);
  // All 3 events need travel blocks
  assert.strictEqual(resBody.inserted.length, 3);
  // Each inserted block must have [Travel] prefix
  for (const summary of insertedSummaries) {
    assert.ok(summary.startsWith("[Travel]"), `"${summary}" must start with [Travel]`);
  }
});

// ── Test 7: Token refresh via GOOGLE_REFRESH_TOKEN ───────────────────────────

test("handler refreshes token via OAuth2 when GOOGLE_CALENDAR_TOKEN is absent", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  process.env.GOOGLE_REFRESH_TOKEN = "rtoken-test";
  process.env.GOOGLE_CLIENT_ID = "client-id-test";
  process.env.GOOGLE_CLIENT_SECRET = "client-secret-test";

  let tokenRefreshCalled = false;
  let gcalListCalled = false;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("oauth2.googleapis.com/token")) {
      tokenRefreshCalled = true;
      // Verify the refresh request has correct fields
      const body = opts.body;
      assert.ok(body.includes("grant_type=refresh_token"), "must send refresh_token grant type");
      assert.ok(body.includes("rtoken-test"), "must include refresh token");
      return {
        ok: true,
        json: async () => ({ access_token: "refreshed-access-tok", expires_in: 3600 }),
      };
    }
    if (url.includes("calendar/v3")) {
      gcalListCalled = true;
      // Verify it uses the refreshed token
      assert.ok(opts.headers.Authorization.includes("refreshed-access-tok"), "must use refreshed token");
      return { ok: true, json: async () => gcalListResponse([]) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  assert.ok(tokenRefreshCalled, "OAuth2 token refresh must be called");
  assert.ok(gcalListCalled, "GCal list must be called after token refresh");
});

// ── Test 8: All-day events are skipped (no departure time to anchor block) ────

test("handler skips all-day events when detecting missing travel blocks", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "tok-static";

  const events = [
    { id: "ev1", summary: "Holiday", start: { date: "2026-06-17" }, end: { date: "2026-06-17" } },
  ];

  let insertCalled = false;

  globalThis.fetch = async (url, opts) => {
    if (url.includes("calendar/v3") && (!opts || opts.method !== "POST")) {
      return { ok: true, json: async () => gcalListResponse(events) };
    }
    if (url.includes("calendar/v3") && opts && opts.method === "POST") {
      insertCalled = true;
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const { handler } = require("../../life-travel");
  const res = await handler({ httpMethod: "POST" });

  assert.strictEqual(res.statusCode, 200);
  assert.ok(!insertCalled, "must NOT insert travel block for all-day event");
  const resBody = JSON.parse(res.body);
  assert.strictEqual(resBody.inserted.length, 0);
});

// ── Test 9: gcal-token module — getAccessToken static path ───────────────────

test("gcal-token.getAccessToken returns static token when GOOGLE_CALENDAR_TOKEN is set", async () => {
  process.env.GOOGLE_CALENDAR_TOKEN = "static-tok-xyz";

  const { getAccessToken } = require("../gcal-token");
  const tok = await getAccessToken();
  assert.strictEqual(tok, "static-tok-xyz");
});

// ── Test 10: gcal-token module — refresh path ────────────────────────────────

test("gcal-token.getAccessToken refreshes when only refresh token set", async () => {
  delete process.env.GOOGLE_CALENDAR_TOKEN;
  process.env.GOOGLE_REFRESH_TOKEN = "rtest";
  process.env.GOOGLE_CLIENT_ID = "cidtest";
  process.env.GOOGLE_CLIENT_SECRET = "csectest";

  globalThis.fetch = async (url) => {
    assert.ok(url.includes("oauth2.googleapis.com/token"), "must call token endpoint");
    return { ok: true, json: async () => ({ access_token: "new-token-abc" }) };
  };

  const { getAccessToken } = require("../gcal-token");
  const tok = await getAccessToken();
  assert.strictEqual(tok, "new-token-abc");
});
