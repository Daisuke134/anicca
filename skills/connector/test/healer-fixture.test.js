"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { observedEffect } = require("../lib/healer-fixture.js");

test("shadow healer restores the expected applied bundle effect", () => {
  assert.equal(observedEffect(), "applied_bundle");
});
