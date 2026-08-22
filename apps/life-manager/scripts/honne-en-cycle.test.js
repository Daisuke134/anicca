"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { parseArgs, runSlot } = require("./honne-en-cycle.js");

const SLOT = "2026-08-21T11:30:00.000Z";

test("Honne EN cycle accepts a manual run timestamp without cadence blocking", () => {
  assert.equal(runSlot(SLOT, Date.parse("2026-08-21T09:00:00.000Z")), SLOT);
  assert.equal(runSlot("2026-08-21T09:00:00.000Z", Date.parse("2026-08-21T09:00:00.000Z")), "2026-08-21T09:00:00.000Z");
  assert.throws(() => runSlot("not-an-instant", Date.now()), /timestamp is invalid/i);
});

test("Honne EN scheduled runs resolve to one exact idempotent slot", () => {
  assert.equal(runSlot(null, Date.parse("2026-08-21T02:45:00.000Z")), "2026-08-21T02:00:00.000Z");
  assert.equal(runSlot(null, Date.parse("2026-08-21T11:45:00.000Z")), "2026-08-21T11:30:00.000Z");
  assert.throws(() => runSlot(null, Date.parse("2026-08-20T21:59:00.000Z")), /no due slot/i);
});

test("Honne EN cycle CLI accepts only the optional slot pair", () => {
  assert.equal(parseArgs(["run"]), null);
  assert.equal(parseArgs(["run", "--slot", SLOT]), SLOT);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage|invalid/i);
  assert.throws(() => parseArgs(["run", "--other", SLOT]), /usage|invalid/i);
});
