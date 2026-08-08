"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { fixture } = require("./mobile-contract-support.js");

test("Gate 3 contract declares the complete mobile v1 surface", () => {
  const contract = fixture("contract.json");
  assert.equal(contract.version, "mobile-v1");
  assert.equal(contract.locale, "en");
  assert.deepEqual(contract.forbiddenSurfaces, ["late_notice", "scheduler", "cost_guard"]);
  assert.deepEqual(contract.endpoints.map((endpoint) => `${endpoint.method} ${endpoint.path}`), [
    "POST /session/calendar/start",
    "POST /session/exchange",
    "POST /session/refresh",
    "DELETE /session",
    "GET /bootstrap",
    "PATCH /profile",
    "POST /analysis",
    "GET /chat",
    "POST /questions/{id}/reply",
    "POST /calls/test",
    "PUT /devices/apns",
    "DELETE /devices/apns",
    "DELETE /account",
  ]);
  for (const endpoint of contract.endpoints) {
    assert.equal(endpoint.path.startsWith("/api/mobile/v1"), false, "fixture paths are router-relative");
    assert.equal(endpoint.requiresBearer, !endpoint.path.startsWith("/session/"));
    assert.equal(endpoint.mutation ? endpoint.idempotencyKey : false, endpoint.mutation);
  }
});
