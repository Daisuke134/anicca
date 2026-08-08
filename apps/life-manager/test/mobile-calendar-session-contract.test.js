"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertIso,
  assertOpaque,
  assertNoClientAuthority,
} = require("./mobile-contract-support.js");

test("mobile session fixtures freeze one-use calendar start and bearer exchange", () => {
  const start = fixture("session-start.json");
  const session = fixture("session.json");

  assert.deepEqual(Object.keys(start).sort(), ["authorizationUrl", "expiresAt", "state"].sort());
  assert.equal(typeof start.authorizationUrl, "string");
  assert.match(start.authorizationUrl, /^https:\/\//u);
  assertOpaque(start.state, "session state");
  assertIso(start.expiresAt, "session state expiry");

  assert.deepEqual(Object.keys(session).sort(), [
    "accessToken", "expiresAt", "refreshExpiresAt", "refreshToken", "tokenType",
  ].sort());
  assert.equal(session.tokenType, "Bearer");
  assertOpaque(session.accessToken, "access token");
  assertOpaque(session.refreshToken, "refresh token");
  assertIso(session.expiresAt, "access token expiry");
  assertIso(session.refreshExpiresAt, "refresh token expiry");
  assert.equal(Date.parse(session.refreshExpiresAt) > Date.parse(session.expiresAt), true);
  assertNoClientAuthority(start, "session start");
  assertNoClientAuthority(session, "session exchange");
});

test("session contract requires rotating refresh semantics and never accepts a client uid", () => {
  const contract = fixture("contract.json");
  assert.equal(contract.version, "mobile-v1");
  assert.equal(contract.session.refreshRotation, "required");
  assert.equal(contract.session.replayRevokesFamily, true);
  assert.equal(contract.session.uidSource, "validated_identity_server_side");
  assert.deepEqual(contract.session.clientAuthorityFields, []);
});
