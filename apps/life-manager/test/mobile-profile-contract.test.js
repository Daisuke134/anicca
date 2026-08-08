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
  assertAllowedKeys(bootstrap, ["analysis", "calendar", "product", "user"], "bootstrap");
  assertAllowedKeys(bootstrap.product, ["locale", "timezone"], "bootstrap.product");
  assert.equal(bootstrap.product.locale, "en");
  assert.equal(typeof bootstrap.product.timezone, "string");
  assertAllowedKeys(bootstrap.user, ["home", "id", "name"], "bootstrap.user");
  assert.equal(bootstrap.user.name, null);
  assertAllowedKeys(bootstrap.user.home, ["display", "status"], "bootstrap.user.home");
  assert.equal(bootstrap.user.home.status, "missing");
  assert.equal(bootstrap.user.home.display, null);
  assertOpaque(bootstrap.user.id, "server-derived bootstrap user id");
  assert.deepEqual(bootstrap.calendar, { status: "connected" });
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

test("contract directory contains only declared Gate 2 JSON fixtures", () => {
  const contract = fixture("contract.json");
  assert.deepEqual(fixtureNames(), [...contract.fixtures].sort());
});
