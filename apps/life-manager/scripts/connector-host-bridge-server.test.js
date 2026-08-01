"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createConnectorHostBridgeClient } = require("../lib/connector-host-bridge.js");
const { createConnectorHostBridgeServer } = require("./connector-host-bridge-server.js");

const TOKEN = "c".repeat(64);

async function withServer(run) {
  const server = createConnectorHostBridgeServer({
    token: TOKEN,
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() { return []; },
      async findConnectorEvents() { return []; },
      async createConnectorEvent() { return { id: "created" }; },
    },
    async routeMinutes() { return 12; },
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  try {
    const port = server.address().port;
    await run(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("real localhost HTTP server serves the authenticated bridge client", async () => {
  await withServer(async (baseUrl) => {
    const client = createConnectorHostBridgeClient({ baseUrl, token: TOKEN });
    assert.deepEqual(await client.calendar.listCalendarsRaw({ strict: true }), [{ id: "primary" }]);
    assert.equal(await client.routeMinutes({ from: "A", to: "B" }), 12);
  });
});

test("HTTP boundary rejects wrong method, path, content type, bad JSON, auth, and oversized bodies generically", async () => {
  await withServer(async (baseUrl) => {
    const request = (path, init) => fetch(`${baseUrl}${path}`, init);
    assert.equal((await request("/v1/connector", { method: "GET" })).status, 404);
    assert.equal((await request("/other", { method: "POST" })).status, 404);
    assert.equal((await request("/v1/connector", {
      method: "POST", headers: { "Content-Type": "text/plain" }, body: "{}",
    })).status, 415);
    assert.equal((await request("/v1/connector", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "not-json",
    })).status, 400);
    const denied = await request("/v1/connector", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer wrong" },
      body: JSON.stringify({ operation: "calendar.list", input: {} }),
    });
    assert.equal(denied.status, 503);
    assert.deepEqual(await denied.json(), { ok: false, error: "bridge_unavailable" });
    assert.equal((await request("/v1/connector", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
      body: JSON.stringify({ operation: "calendar.list", input: { padding: "x".repeat(20_000) } }),
    })).status, 413);
  });
});
