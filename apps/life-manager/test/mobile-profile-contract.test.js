"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  fixtureNames,
  assertGeneratedEnglish,
  assertNoClientAuthority,
  assertAllowedKeys,
  assertOpaque,
} = require("./mobile-contract-support.js");

test("mobile bootstrap freezes English demo profile and calendar state", () => {
  const bootstrap = fixture("bootstrap.json");
  assertAllowedKeys(bootstrap, ["analysis", "calendar", "offer", "user"], "bootstrap");
  assertAllowedKeys(bootstrap.user, ["callLanguage", "callsEnabled", "home", "id", "name", "phone", "productLocale", "timezone"], "bootstrap.user");
  assert.equal(bootstrap.user.name, null);
  assertAllowedKeys(bootstrap.user.home, ["display", "status"], "bootstrap.user.home");
  assert.equal(bootstrap.user.home.status, "missing");
  assert.equal(bootstrap.user.home.display, null);
  assert.equal(bootstrap.user.productLocale, "en");
  assert.equal(typeof bootstrap.user.timezone, "string");
  assert.deepEqual(bootstrap.user.phone, { status: "missing", masked: null });
  assert.equal(bootstrap.user.callsEnabled, false);
  assert.equal(bootstrap.user.callLanguage, null);
  assertOpaque(bootstrap.user.id, "server-derived bootstrap user id");
  assert.deepEqual(bootstrap.calendar, { status: "connected" });
  assert.deepEqual(bootstrap.offer, { status: "available" });
  assert.deepEqual(bootstrap.analysis, { status: "idle" });
  assertGeneratedEnglish(bootstrap, "bootstrap");
  assertNoClientAuthority(bootstrap, "bootstrap");
});

test("profile patch is allowlisted to name, home, and English product locale", () => {
  const patch = fixture("profile-patch.json");
  assertAllowedKeys(patch, ["home", "name", "productLocale"], "profile patch");
  assert.equal(typeof patch.name, "string");
  assert.equal(typeof patch.home, "string");
  assert.equal(patch.productLocale, "en");
  assertNoClientAuthority(patch, "profile patch");
});

test("contract directory contains only declared Gate 3 JSON fixtures", () => {
  const contract = fixture("contract.json");
  assert.deepEqual(fixtureNames(), [...contract.fixtures].sort());
});
