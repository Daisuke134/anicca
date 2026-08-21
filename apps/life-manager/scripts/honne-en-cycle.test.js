"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { dueSlot, parseArgs } = require("./honne-en-cycle.js");

const SLOT = "2026-08-21T11:30:00.000Z";

test("Honne EN cycle accepts only a due cadence slot inside the grace window", () => {
  assert.equal(dueSlot(SLOT, Date.parse("2026-08-21T11:35:00.000Z")), SLOT);
  assert.throws(() => dueSlot(SLOT, Date.parse("2026-08-21T11:00:00.000Z")), /not within/i);
  assert.throws(() => dueSlot("2026-08-21T12:00:00.000Z", Date.parse("2026-08-21T12:01:00.000Z")), /off cadence/i);
  assert.throws(() => dueSlot(SLOT, Date.parse("2026-08-21T12:00:00.000Z")), /not within/i);
});

test("Honne EN cycle CLI accepts only the optional slot pair", () => {
  assert.equal(parseArgs(["run"]), null);
  assert.equal(parseArgs(["run", "--slot", SLOT]), SLOT);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage|invalid/i);
  assert.throws(() => parseArgs(["run", "--other", SLOT]), /usage|invalid/i);
});
