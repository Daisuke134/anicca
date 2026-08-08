"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  deriveTravelProviderEventId,
  ensureMobileTravelBlock,
  canonicalTravelPayload,
} = require("../lib/mobile-travel-block.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");
const { makeComposioCalendar } = require("../lib/transport/calendar-composio.js");

const SECRET = "travel-block-test-secret-2026";
const BASE = Object.freeze({
  uid: "lm_stable_user",
  eventKey: "source-event-1",
  sourceEventId: "source-event-1",
  analysisKey: "analysis-1",
  leg: "go",
  calendarId: "primary",
  payload: {
    summary: "[Travel] Home to Studio",
    description: "Life Manager travel block",
    location: "Studio Station",
    start: { dateTime: "2026-08-10T08:00:00+09:00", timeZone: "Asia/Tokyo" },
    end: { dateTime: "2026-08-10T08:30:00+09:00", timeZone: "Asia/Tokyo" },
  },
  composioUserId: "lm_composio_provisional",
  connectedAccountId: "ca_exact_account",
});

function input(overrides = {}) {
  return { ...BASE, ...overrides, payload: { ...BASE.payload, ...(overrides.payload || {}) } };
}

function providerEvent(overrides = {}) {
  return {
    id: overrides.id,
    summary: BASE.payload.summary,
    description: BASE.payload.description,
    location: BASE.payload.location,
    start: { ...BASE.payload.start },
    end: { ...BASE.payload.end },
    extendedProperties: { private: { lm_travel_block: overrides.marker } },
    etag: '"etag-1"',
    ...overrides,
  };
}

function makeProvider({ get, post, statuses = {} } = {}) {
  const calls = [];
  return {
    calls,
    async getExactEvent(_uid, args) {
      calls.push({ kind: "get", args: { ...args } });
      const result = typeof get === "function" ? await get(args, calls) : { status: 404, data: null };
      return { ...result, status: result.status == null ? statuses.get || 404 : result.status };
    },
    async createExactEvent(_uid, args) {
      calls.push({ kind: "post", args: { ...args } });
      const result = typeof post === "function" ? await post(args, calls) : { status: 201, data: null };
      return { ...result, status: result.status == null ? statuses.post || 201 : result.status };
    },
  };
}

test("deterministic provider event IDs are stable, separated by tuple, and Google-valid", () => {
  const first = deriveTravelProviderEventId({ secret: SECRET, uid: "lm_a", calendarId: "primary", sourceEventId: "evt", leg: "go" });
  const same = deriveTravelProviderEventId({ secret: SECRET, uid: "lm_a", calendarId: "primary", sourceEventId: "evt", leg: "go" });
  const differentLeg = deriveTravelProviderEventId({ secret: SECRET, uid: "lm_a", calendarId: "primary", sourceEventId: "evt", leg: "return" });
  const differentEvent = deriveTravelProviderEventId({ secret: SECRET, uid: "lm_a", calendarId: "primary", sourceEventId: "evt-2", leg: "go" });
  assert.equal(first, same);
  assert.notEqual(first, differentLeg);
  assert.notEqual(first, differentEvent);
  assert.match(first, /^lm[a-v0-9]{64}$/u);
  assert.ok(first.length >= 5 && first.length <= 1024);
});

test("canonical payload hashing ignores key order but changes event facts", () => {
  const a = canonicalTravelPayload(BASE.payload);
  const b = canonicalTravelPayload({ end: BASE.payload.end, start: BASE.payload.start, location: BASE.payload.location, summary: BASE.payload.summary, description: BASE.payload.description });
  assert.equal(a.hash, b.hash);
  assert.notEqual(a.hash, canonicalTravelPayload({ ...BASE.payload, location: "Different Station" }).hash);
});

test("proxy contract uses exact connected account and never stable UID as provider owner", async () => {
  const calls = [];
  const calendar = makeComposioCalendar({
    apiKey: "composio-proxy-key",
    recordCall: async () => false,
    authorizeProviderOperation: async () => ({ allowed: true }),
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), body: JSON.parse(init.body) });
      return { ok: true, status: 200, async json() { return { status: 404, data: null, headers: {} }; } };
    },
  });
  await calendar.getExactEvent("lm_stable_user", {
    calendarId: "primary", providerEventId: "lmx", composioUserId: "owner_exact", connectedAccountId: "ca_exact_account",
  });
  assert.equal(calls[0].url, "https://backend.composio.dev/api/v3.1/tools/execute/proxy");
  assert.equal(calls[0].body.connected_account_id, "ca_exact_account");
  assert.equal(calls[0].body.method, "GET");
  assert.equal(calls[0].body.endpoint, "/calendars/primary/events/lmx");
  assert.equal(Object.hasOwn(calls[0].body, "user_id"), false);
  assert.equal(Object.hasOwn(calls[0].body, "uid"), false);
});

test("proxy create contract is v3.1 only and sends the exact Google POST body", async () => {
  const calls = [];
  const calendar = makeComposioCalendar({
    apiKey: "composio-proxy-key",
    recordCall: async () => false,
    authorizeProviderOperation: async () => ({ allowed: true }),
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), body: JSON.parse(init.body) });
      return { ok: true, status: 200, async json() { return { status: 201, data: { id: "lmx" }, headers: {} }; } };
    },
  });
  await calendar.createExactEvent("lm_stable_user", {
    calendarId: "primary", providerEventId: "lmx", composioUserId: "owner_exact", connectedAccountId: "ca_exact_account",
    body: {
      id: "must-be-replaced",
      summary: "[Travel] Home to Studio",
      start: { dateTime: "2026-08-10T08:00:00+09:00", timeZone: "Asia/Tokyo" },
      end: { dateTime: "2026-08-10T08:30:00+09:00", timeZone: "Asia/Tokyo" },
      extendedProperties: { private: { lm_travel_block: "opaque-marker" } },
    },
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://backend.composio.dev/api/v3.1/tools/execute/proxy");
  assert.doesNotMatch(calls[0].url, /\/api\/v3\/tools\/execute(?:\/|$)/u);
  assert.equal(calls[0].body.connected_account_id, "ca_exact_account");
  assert.equal(calls[0].body.endpoint, "/calendars/primary/events");
  assert.equal(calls[0].body.method, "POST");
  assert.equal(calls[0].body.body.id, "lmx");
  assert.equal(calls[0].body.body.extendedProperties.private.lm_travel_block, "opaque-marker");
  assert.equal(Object.hasOwn(calls[0].body, "user_id"), false);
});

test("mobile primary-calendar identity read uses Composio v3.1 and never falls back to v3", async () => {
  const calls = [];
  const calendar = makeComposioCalendar({
    apiKey: "composio-tool-key",
    recordCall: async () => false,
    authorizeProviderOperation: async () => ({ allowed: true }),
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), body: JSON.parse(init.body) });
      return { ok: true, status: 200, async json() { return { successful: true, data: { response_data: { items: [{ id: "calendar-owner" }] } } }; } };
    },
  });
  const primary = await calendar.readPrimaryCalendar("lm_stable_user", { connectedAccountId: "ca_exact_account" });
  assert.equal(primary.id, "calendar-owner");
  assert.equal(calls[0].url, "https://backend.composio.dev/api/v3.1/tools/execute/GOOGLECALENDAR_CALENDAR_LIST_GET");
  assert.doesNotMatch(calls[0].url, /\/api\/v3\/tools\/execute(?:\/|$)/u);
  assert.equal(calls[0].body.connected_account_id, "ca_exact_account");
});

test("create waits for mark_create_started and includes deterministic ID and private marker", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  const provider = makeProvider({
    get: async (_args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: calls[0].args.providerEventId, marker: calls[1]?.args.marker }) },
    post: async () => ({ status: 201, data: {} }),
  });
  const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET, workerId: "worker-a" });
  assert.equal(result.status, "created");
  assert.equal(provider.calls.filter((call) => call.kind === "post").length, 1);
  assert.deepEqual(provider.calls[1].args.body.extendedProperties.private, { lm_travel_block: result.marker });
  assert.equal(provider.calls[1].args.body.id, result.providerEventId);
  assert.equal(provider.calls[1].args.body.user_id, undefined);
});

test("two concurrent workers yield one create and one busy claim", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  let release;
  const pause = new Promise((resolve) => { release = resolve; });
  const provider = makeProvider({
    get: async () => { await pause; return { status: 404 }; },
    post: async () => ({ status: 201, data: {} }),
  });
  const first = ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET, workerId: "worker-a" });
  await new Promise((resolve) => setImmediate(resolve));
  const second = ensureMobileTravelBlock(input({ analysisKey: "analysis-2" }), { store, provider, serverSecret: SECRET, workerId: "worker-b" });
  release();
  const results = await Promise.all([first, second]);
  assert.equal(provider.calls.filter((call) => call.kind === "post").length, 1);
  assert.ok(results.some((row) => ["busy", "claim_pending", "created"].includes(row.status)));
});

test("same payload on another analysis key reuses one confirmed operation", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  const provider = makeProvider({ get: async (args) => ({ status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) }) });
  const first = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET, workerId: "worker-a" });
  const second = await ensureMobileTravelBlock(input({ analysisKey: "analysis-2" }), { store, provider, serverSecret: SECRET, workerId: "worker-b" });
  assert.equal(first.status, "existing");
  assert.equal(second.status, "existing");
  assert.equal(provider.calls.filter((call) => call.kind === "post").length, 0);
});

test("different payload fails closed without a provider call", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  const provider = makeProvider({ get: async () => ({ status: 404 }), post: async () => ({ status: 201 }) });
  const first = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
  assert.equal(first.status, "provider_readback_failed");
  const callsAfterFirst = provider.calls.length;
  const conflict = await ensureMobileTravelBlock(input({ payload: { location: "Another Station" }, analysisKey: "analysis-2" }), { store, provider, serverSecret: SECRET });
  assert.equal(conflict.status, "analysis_conflict");
  assert.equal(provider.calls.length, callsAfterFirst, "analysis conflict must not reach the provider");
});

test("stale claim rotates token and stale worker cannot confirm or release", async () => {
  let now = Date.parse("2026-08-10T00:00:00.000Z");
  const store = createMemoryMobileStore({ now: () => now });
  const first = await store.claimTravelBlock({ ...input(), payloadHash: canonicalTravelPayload(BASE.payload).hash, marker: "marker-a", providerEventId: "lm" + "a".repeat(64), claimWorkerId: "worker-a", leaseMs: 1000 });
  now += 2000;
  const second = await store.claimTravelBlock({ ...input(), payloadHash: first.payloadHash, marker: first.marker, providerEventId: first.providerEventId, claimWorkerId: "worker-b", leaseMs: 1000 });
  assert.notEqual(second.claimToken, first.claimToken);
  assert.equal((await store.confirmTravelBlock({ ...input(), claimToken: first.claimToken })).confirmed, false);
  assert.equal((await store.releaseTravelClaim({ ...input(), claimToken: first.claimToken })).released, false);
});

test("a crash before create is recoverable and the recovery uses the same event ID", async () => {
  let now = Date.parse("2026-08-10T00:00:00.000Z");
  const store = createMemoryMobileStore({ now: () => now });
  const seed = await ensureMobileTravelBlock(input({ leaseSeconds: 1 }), {
    store,
    provider: makeProvider({ get: async () => ({ status: 500 }) }),
    serverSecret: SECRET,
  });
  assert.equal(seed.status, "provider_readback_failed");
  now += 2_000;
  const provider = makeProvider({
    get: async (args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) },
    post: async () => ({ status: 201 }),
  });
  const recovered = await ensureMobileTravelBlock(input({ leaseSeconds: 1 }), { store, provider, serverSecret: SECRET });
  assert.equal(recovered.status, "created");
  assert.equal(provider.calls.filter((call) => call.kind === "post").length, 1);
  assert.equal(provider.calls.filter((call) => call.kind === "post")[0].args.providerEventId, seed.providerEventId);
});

test("a crash after provider success confirms by GET without a second POST", async () => {
  let now = Date.parse("2026-08-10T00:00:00.000Z");
  const store = createMemoryMobileStore({ now: () => now });
  const firstProvider = makeProvider({ get: async () => ({ status: 404 }), post: async () => ({ status: 201 }) });
  const first = await ensureMobileTravelBlock(input({ leaseSeconds: 1 }), { store, provider: firstProvider, serverSecret: SECRET });
  assert.equal(first.status, "provider_readback_failed");
  const row = await store.readTravelBlock(input());
  await store.markTravelCreateStarted({ ...input(), claimToken: row.claimToken, now: new Date(now).toISOString() });
  now += 2_000;
  const provider = makeProvider({ get: async (args) => ({ status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) }), post: async () => ({ status: 201 }) });
  const recovered = await ensureMobileTravelBlock(input({ leaseSeconds: 1 }), { store, provider, serverSecret: SECRET });
  assert.equal(recovered.status, "existing");
  assert.equal(provider.calls.filter((call) => call.kind === "post").length, 0);
});

test("a mismatched successful read-back never becomes a success", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  const provider = makeProvider({
    get: async (_args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: calls[0].args.providerEventId, marker: "wrong-marker" }) },
    post: async () => ({ status: 201 }),
  });
  const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
  assert.equal(result.status, "provider_readback_failed");
  assert.notEqual(result.status, "created");
  assert.notEqual((await store.readTravelBlock(input())).status, "confirmed");
});

test("post timeout, 409 match, and 409 collision all use exact GET read-back", async (t) => {
  await t.test("timeout then exact GET confirms", async () => {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    const provider = makeProvider({
      get: async (args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) },
      post: async () => { throw new Error("timeout"); },
    });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "existing");
  });
  await t.test("409 with exact GET confirms", async () => {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    const provider = makeProvider({
      get: async (args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) },
      post: async () => ({ status: 409, data: {} }),
    });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "existing");
  });
  await t.test("409 with mismatched GET blocks collision and never changes ID", async () => {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    const provider = makeProvider({
      get: async (args, calls) => calls.filter((call) => call.kind === "get").length === 1 ? { status: 404 } : { status: 200, data: providerEvent({ id: args.providerEventId, marker: "other-marker" }) },
      post: async () => ({ status: 409, data: {} }),
    });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "provider_collision");
    assert.equal(provider.calls.filter((call) => call.kind === "post").length, 1);
    assert.equal(provider.calls.filter((call) => call.kind === "get").at(-1).args.providerEventId, result.providerEventId);
  });
});

test("initial GET failure never reaches POST", async () => {
  for (const status of [403, 429, 500]) {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    const provider = makeProvider({ get: async () => ({ status }), post: async () => ({ status: 201 }) });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "provider_readback_failed");
    assert.equal(provider.calls.filter((call) => call.kind === "post").length, 0);
  }
});

test("blocked collision is terminal on every retry and is never reported as existing", async () => {
  const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
  let reads = 0;
  const provider = makeProvider({
    get: async (args) => {
      reads += 1;
      if (reads === 1) return { status: 404 };
      return { status: 200, data: providerEvent({ id: args.providerEventId, marker: "different-marker" }) };
    },
    post: async () => ({ status: 409 }),
  });
  const first = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
  assert.equal(first.status, "provider_collision");
  const callsAfterCollision = provider.calls.length;
  const second = await ensureMobileTravelBlock(input({ analysisKey: "analysis-retry" }), { store, provider, serverSecret: SECRET });
  assert.equal(second.status, "provider_collision");
  assert.equal(second.errorCode, "provider_collision");
  assert.equal(provider.calls.length, callsAfterCollision, "a terminal collision must make zero provider calls on retry");
  assert.equal((await store.readTravelBlock(input())).status, "blocked_collision");
});

test("provider proxy requires a durable owner/account pair and passes the exact pair", async () => {
  const noOwnerCalls = [];
  const calendar = makeComposioCalendar({
    apiKey: "composio-proxy-key",
    recordCall: async () => false,
    authorizeProviderOperation: async () => ({ allowed: true }),
    fetchImpl: async (...args) => {
      noOwnerCalls.push(args);
      return { ok: true, status: 200, async json() { return { status: 404, data: null, headers: {} }; } };
    },
  });
  await calendar.getExactEvent("lm_stable_user", { calendarId: "primary", providerEventId: "lmx", connectedAccountId: "ca_exact_account" });
  assert.equal(noOwnerCalls.length, 0, "missing provisional owner must not reach Proxy");

  const noAccountCalls = [];
  const noAccountCalendar = makeComposioCalendar({
    apiKey: "composio-proxy-key",
    recordCall: async () => false,
    authorizeProviderOperation: async () => ({ allowed: true }),
    fetchImpl: async (...args) => {
      noAccountCalls.push(args);
      return { ok: true, status: 200, async json() { return { status: 404, data: null, headers: {} }; } };
    },
  });
  await noAccountCalendar.getExactEvent("lm_stable_user", { calendarId: "primary", providerEventId: "lmx", composioUserId: "owner_exact" });
  assert.equal(noAccountCalls.length, 0, "missing exact connected account must not reach Proxy");

  const store = createMemoryMobileStore({
    now: () => Date.parse("2026-08-10T00:00:00.000Z"),
    users: [{ uid: BASE.uid, calendar_composio_user_id: "owner-durable", gmail_account_id: "account-durable" }],
  });
  const provider = makeProvider({
    get: async (args, calls) => calls.filter((call) => call.kind === "get").length === 1
      ? { status: 404 }
      : { status: 200, data: providerEvent({ id: args.providerEventId, marker: args.marker }) },
    post: async () => ({ status: 201 }),
  });
  const missing = await ensureMobileTravelBlock(input({ composioUserId: null }), {
    store, provider, serverSecret: SECRET,
  });
  assert.equal(missing.status, "provider_binding_invalid");
  assert.equal(provider.calls.length, 0, "missing durable binding must make zero provider calls");
  const mismatch = await ensureMobileTravelBlock(input({ composioUserId: "owner-wrong", connectedAccountId: "account-wrong" }), {
    store, provider, serverSecret: SECRET,
  });
  assert.equal(mismatch.status, "provider_binding_invalid");
  assert.equal(provider.calls.length, 0, "mismatched durable binding must make zero provider calls");

  const exact = await ensureMobileTravelBlock(input({ composioUserId: "owner-durable", connectedAccountId: "account-durable" }), {
    store, provider, serverSecret: SECRET,
  });
  assert.equal(exact.status, "created");
  for (const call of provider.calls) {
    assert.equal(call.args.composioUserId, "owner-durable");
    assert.equal(call.args.connectedAccountId, "account-durable");
  }
});

test("budget, write, and readback failures retain their bounded taxonomy", async (t) => {
  await t.test("budget denial on exact GET", async () => {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    const provider = makeProvider({
      get: async () => { const error = new Error("budget"); error.code = "budget_denied"; throw error; },
      post: async () => ({ status: 201 }),
    });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "budget_denied");
    assert.equal(provider.calls.filter((call) => call.kind === "post").length, 0);
    assert.equal((await store.readTravelBlock(input())).lastErrorCode, "budget_denied");
  });

  for (const [label, postOutcome] of [
    ["400", { status: 400 }],
    ["500", { status: 500 }],
    ["timeout", Object.assign(new Error("timeout"), { code: "timeout" })],
  ]) {
    await t.test(`POST ${label} is a provider write failure when exact readback is absent`, async () => {
      const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
      const provider = makeProvider({
        get: async () => ({ status: 404 }),
        post: async () => { if (postOutcome instanceof Error) throw postOutcome; return postOutcome; },
      });
      const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
      assert.equal(result.status, "provider_write_failed");
      assert.equal(result.errorCode, "provider_write_failed");
      assert.equal((await store.readTravelBlock(input())).lastErrorCode, "provider_write_failed");
    });
  }

  await t.test("a write outcome with an unavailable exact readback remains readback failure", async () => {
    const store = createMemoryMobileStore({ now: () => Date.parse("2026-08-10T00:00:00.000Z") });
    let reads = 0;
    const provider = makeProvider({
      get: async () => (++reads === 1 ? { status: 404 } : { status: 503 }),
      post: async () => ({ status: 400 }),
    });
    const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
    assert.equal(result.status, "provider_readback_failed");
    assert.equal(result.errorCode, "provider_readback_failed");
    assert.equal((await store.readTravelBlock(input())).lastErrorCode, "provider_readback_failed");
  });
});

test("legacy pre-migration row remains terminal and is never recreated", async () => {
  const store = createMemoryMobileStore({
    now: () => Date.parse("2026-08-10T00:00:00.000Z"),
    travelBlocks: [{ uid: BASE.uid, event_key: BASE.eventKey, leg: BASE.leg }],
  });
  const provider = makeProvider({ post: async () => ({ status: 201 }) });
  const result = await ensureMobileTravelBlock(input(), { store, provider, serverSecret: SECRET });
  assert.equal(result.status, "legacy_terminal");
  assert.equal(provider.calls.length, 0);
});

test("migration has durable fields, token-fenced RPCs, and service-role-only grants", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-09-lm-travel-block-state.sql"), "utf8");
  for (const column of ["status", "calendar_id", "analysis_key", "payload_hash", "marker", "provider_event_id", "composio_user_id", "connected_account_id", "provider_etag", "claim_token", "claim_worker_id", "claim_acquired_at", "lease_expires_at", "create_started_at", "provider_observed_at", "confirmed_at", "attempt_count", "last_error_code", "updated_at"]) assert.match(sql, new RegExp(`\\b${column}\\b`));
  for (const fn of ["claim_lm_travel_block", "mark_lm_travel_create_started", "confirm_lm_travel_block", "release_lm_travel_claim", "block_lm_travel_collision"]) {
    assert.match(sql, new RegExp(`CREATE OR REPLACE FUNCTION public\\.${fn}\\b`));
    assert.match(sql, new RegExp(`REVOKE ALL ON FUNCTION public\\.${fn}`));
    assert.match(sql, new RegExp(`GRANT EXECUTE ON FUNCTION public\\.${fn}[^\\n]*TO service_role`));
  }
  assert.match(sql, /UNIQUE \(uid, event_key, leg\)/);
  assert.match(sql, /CREATE UNIQUE INDEX IF NOT EXISTS lm_travel_log_provider_event_unique/);
  assert.match(sql, /CREATE UNIQUE INDEX IF NOT EXISTS lm_travel_log_marker_unique/);
  assert.match(sql, /legacy_terminal/);
  assert.doesNotMatch(sql, /pg_advisory_(?:lock|xact_lock|unlock)/i);
});
