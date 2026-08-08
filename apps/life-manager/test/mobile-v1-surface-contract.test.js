"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { fixture } = require("./mobile-contract-support.js");

test("Gate 2 contract declares only the English demo mobile surface", () => {
  const contract = fixture("contract.json");
  assert.equal(contract.version, "mobile-v1");
  assert.equal(contract.locale, "en");
  assert.deepEqual(contract.forbiddenSurfaces, [
    "apns", "account_deletion", "calls", "japanese_localization", "late_notice", "phone",
  ]);
  assert.deepEqual(contract.endpoints.map((endpoint) => `${endpoint.method} ${endpoint.path}`), [
    "POST /session/calendar/start",
    "POST /session/exchange",
    "POST /session/refresh",
    "DELETE /session",
    "GET /bootstrap",
    "PATCH /profile",
    "POST /analysis",
    "GET /chat",
  ]);
  for (const endpoint of contract.endpoints) {
    assert.equal(endpoint.path.startsWith("/api/mobile/v1"), false, "fixture paths are router-relative");
    assert.equal(endpoint.requiresBearer, !endpoint.path.startsWith("/session/"));
    assert.equal(endpoint.mutation ? endpoint.idempotencyKey : false, endpoint.mutation);
  }
});
