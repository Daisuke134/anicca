"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { runSteelCloudSmoke } = require("./steel-cloud-smoke.js");

function fakeClient(overrides = {}) {
  const calls = [];
  return {
    calls,
    baseUrl: "http://steel-browser.railway.internal:3000",
    async health() {
      calls.push(["health"]);
      return true;
    },
    async createSession(options) {
      calls.push(["createSession", options]);
      return {
        id: "session-123",
        websocketUrl: "ws://steel-browser.railway.internal:3000/v1/sessions/session-123",
      };
    },
    async navigate(sessionId, url) {
      calls.push(["navigate", sessionId, url]);
    },
    async readConfirmation(sessionId) {
      calls.push(["readConfirmation", sessionId]);
      return {
        url: "https://example.com/",
        text: "Example Domain\nThis domain is for use in illustrative examples.",
      };
    },
    async releaseSession(sessionId) {
      calls.push(["releaseSession", sessionId]);
      return true;
    },
    ...overrides,
  };
}

test("runs health → real session → navigation → bounded readback → release", async () => {
  const client = fakeClient();

  const result = await runSteelCloudSmoke({
    client,
    targetUrl: "https://example.com/",
    marker: "Example Domain",
    now: () => "2026-07-28T00:00:00.000Z",
  });

  assert.deepEqual(client.calls.map(([kind]) => kind), [
    "health",
    "createSession",
    "navigate",
    "readConfirmation",
    "releaseSession",
  ]);
  assert.deepEqual(client.calls[1][1], {
    timezone: "Asia/Tokyo",
    dimensions: { width: 1280, height: 800 },
  });
  assert.equal(result.ok, true);
  assert.equal(result.health, true);
  assert.equal(result.session_id, "session-123");
  assert.equal(result.websocket_scheme, "ws:");
  assert.deepEqual(result.readback, {
    final_url: "https://example.com/",
    marker_present: true,
  });
  assert.equal(result.released, true);
  assert.equal("text" in result.readback, false, "provider page content must not leak into evidence");
});

test("a page read failure is visible and still releases the only Steel session once", async () => {
  const client = fakeClient({
    async readConfirmation(sessionId) {
      this.calls.push(["readConfirmation", sessionId]);
      throw new Error("CDP target crashed");
    },
  });

  const result = await runSteelCloudSmoke({
    client,
    targetUrl: "https://example.com/",
    marker: "Example Domain",
    now: () => "2026-07-28T00:00:00.000Z",
  });

  assert.equal(result.ok, false);
  assert.match(result.error, /CDP target crashed/);
  assert.equal(result.released, true);
  assert.equal(client.calls.filter(([kind]) => kind === "releaseSession").length, 1);
});

test("an unhealthy Steel service creates no session and cannot claim success", async () => {
  const client = fakeClient({
    async health() {
      this.calls.push(["health"]);
      return false;
    },
  });

  const result = await runSteelCloudSmoke({
    client,
    targetUrl: "https://example.com/",
    marker: "Example Domain",
    now: () => "2026-07-28T00:00:00.000Z",
  });

  assert.equal(result.ok, false);
  assert.match(result.error, /health check failed/);
  assert.equal(result.released, false);
  assert.deepEqual(client.calls.map(([kind]) => kind), ["health"]);
});

test("a target URL containing credentials is rejected before health or evidence output", async () => {
  const client = fakeClient();

  await assert.rejects(
    () => runSteelCloudSmoke({
      client,
      targetUrl: "https://user:secret@example.com/",
      marker: "Example Domain",
      now: () => "2026-07-28T00:00:00.000Z",
    }),
    /credentials/,
  );

  assert.deepEqual(client.calls, []);
});
