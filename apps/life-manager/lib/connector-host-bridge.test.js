"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createConnectorHostBridgeClient,
  dispatchConnectorHostBridge,
} = require("./connector-host-bridge.js");

const TOKEN = "a".repeat(64);

function services() {
  return {
    calendar: {
      async listCalendarsRaw(input) { return [{ id: input.strict ? "primary" : "wrong" }]; },
      async listAllEventsRaw(_uid, input) { return [{ id: input.strict ? "event-1" : "wrong" }]; },
      async findConnectorEvents(input) { return [{ id: input.idempotencyValue }]; },
      async createConnectorEvent(input) { return { id: "created", htmlLink: input.canonicalUrl }; },
    },
    async routeMinutes(input) { return input.from === "A" && input.to === "B" ? 17 : null; },
  };
}

test("host bridge dispatches only the five authenticated Connector operations", async () => {
  const deps = services();
  const auth = `Bearer ${TOKEN}`;
  assert.deepEqual(await dispatchConnectorHostBridge({
    authorization: auth, body: { operation: "calendar.list", input: {} },
  }, { token: TOKEN, ...deps }), [{ id: "primary" }]);
  assert.deepEqual(await dispatchConnectorHostBridge({
    authorization: auth,
    body: { operation: "calendar.events", input: { timeMin: "2026-08-02T00:00:00Z", timeMax: "2026-08-23T00:00:00Z" } },
  }, { token: TOKEN, ...deps }), [{ id: "event-1" }]);
  assert.deepEqual(await dispatchConnectorHostBridge({
    authorization: auth, body: { operation: "calendar.find", input: { idempotencyValue: "b".repeat(64) } },
  }, { token: TOKEN, ...deps }), [{ id: "b".repeat(64) }]);
  assert.deepEqual(await dispatchConnectorHostBridge({
    authorization: auth,
    body: { operation: "calendar.create", input: { canonicalUrl: "https://luma.com/event" } },
  }, { token: TOKEN, ...deps }), { id: "created", htmlLink: "https://luma.com/event" });
  assert.equal(await dispatchConnectorHostBridge({
    authorization: auth, body: { operation: "route.minutes", input: { from: "A", to: "B" } },
  }, { token: TOKEN, ...deps }), 17);
});

test("host bridge rejects missing auth, unknown operations, extra envelope fields, and invalid services", async () => {
  const deps = services();
  await assert.rejects(dispatchConnectorHostBridge({
    authorization: "", body: { operation: "calendar.list", input: {} },
  }, { token: TOKEN, ...deps }), /bridge unavailable/i);
  await assert.rejects(dispatchConnectorHostBridge({
    authorization: `Bearer ${TOKEN}`, body: { operation: "shell.exec", input: {} },
  }, { token: TOKEN, ...deps }), /bridge invalid/i);
  await assert.rejects(dispatchConnectorHostBridge({
    authorization: `Bearer ${TOKEN}`, body: { operation: "calendar.list", input: {}, secret: "x" },
  }, { token: TOKEN, ...deps }), /bridge invalid/i);
  await assert.rejects(dispatchConnectorHostBridge({
    authorization: `Bearer ${TOKEN}`, body: { operation: "route.minutes", input: { from: "A", to: "B" } },
  }, { token: TOKEN, calendar: deps.calendar }), /bridge unavailable/i);
});

test("Docker client implements the Calendar and route interfaces without reflecting its token", async () => {
  const calls = [];
  const client = createConnectorHostBridgeClient({
    baseUrl: "http://host.docker.internal:18793",
    token: TOKEN,
    async fetchImpl(url, init) {
      calls.push({ url, init });
      const request = JSON.parse(init.body);
      return {
        ok: true,
        async json() { return { ok: true, result: request.operation === "route.minutes" ? 23 : [] }; },
      };
    },
  });
  assert.deepEqual(await client.calendar.listCalendarsRaw({ strict: true }), []);
  assert.deepEqual(await client.calendar.listAllEventsRaw(null, {
    timeMin: "2026-08-02T00:00:00Z", timeMax: "2026-08-23T00:00:00Z", maxResults: 2500, strict: true,
  }), []);
  assert.deepEqual(await client.calendar.findConnectorEvents({ idempotencyValue: "b".repeat(64) }), []);
  assert.deepEqual(await client.calendar.createConnectorEvent({ canonicalUrl: "https://luma.com/event" }), []);
  assert.equal(await client.routeMinutes({ from: "A", to: "B" }), 23);
  assert.equal(calls.length, 5);
  assert.ok(calls.every((call) => call.url === "http://host.docker.internal:18793/v1/connector"));
  assert.ok(calls.every((call) => call.init.headers.Authorization === `Bearer ${TOKEN}`));

  const broken = createConnectorHostBridgeClient({
    baseUrl: "http://host.docker.internal:18793",
    token: TOKEN,
    async fetchImpl() { return { ok: false, async json() { throw new Error(TOKEN); } }; },
  });
  await assert.rejects(broken.routeMinutes({ from: "A", to: "B" }), (error) => (
    /bridge unavailable/i.test(error.message) && !error.message.includes(TOKEN)
  ));
});

test("client refuses non-local bridge URLs and short tokens before network access", () => {
  assert.throws(() => createConnectorHostBridgeClient({
    baseUrl: "https://example.com", token: TOKEN, fetchImpl: async () => {},
  }), /bridge invalid/i);
  assert.throws(() => createConnectorHostBridgeClient({
    baseUrl: "http://host.docker.internal:18793", token: "short", fetchImpl: async () => {},
  }), /bridge invalid/i);
});
