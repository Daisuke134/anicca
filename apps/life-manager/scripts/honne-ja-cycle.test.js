"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { ANICCA_MAIN_INSTAGRAM_SLOTS, ANICCA_MAIN_SLOTS, PRODUCTION_SLOTS, parseArgs, runSlot } = require("./honne-ja-cycle.js");

test("Honne JA production cadence has three exact idempotent slots", () => {
  assert.deepEqual([...PRODUCTION_SLOTS], ["08:30", "12:30", "21:30"]);
  assert.equal(runSlot(null, Date.parse("2026-08-22T04:00:00.000Z")), "2026-08-22T03:30:00.000Z");
  assert.equal(runSlot(null, Date.parse("2026-08-22T13:00:00.000Z")), "2026-08-22T12:30:00.000Z");
  assert.throws(() => runSlot(null, Date.parse("2026-08-21T23:29:00.000Z")), /no due slot/i);
});

test("Anicca main Instagram has one exact daily Reel slot", () => {
  assert.deepEqual([...ANICCA_MAIN_INSTAGRAM_SLOTS], ["19:10"]);
  const lane = parseArgs(["run-anicca-main-instagram"]).lane;
  assert.equal(lane.platform, "instagram"); assert.equal(lane.account, "@anicca.jp1");
});

test("Honne JA production CLI accepts only an optional exact slot", () => {
  const slot = "2026-08-22T03:30:00.000Z";
  assert.equal(parseArgs(["run"]).slot, null);
  assert.equal(parseArgs(["run", "--slot", slot]).slot, slot);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage/i);
  assert.throws(() => runSlot("invalid", Date.now()), /timestamp is invalid/i);
});

test("Anicca main uses only its three historical JA widget slots", () => {
  assert.deepEqual([...ANICCA_MAIN_SLOTS], ["08:00", "16:00", "22:37"]);
  assert.equal(parseArgs(["run-anicca-main"]).lane.account, "@anicca.jp");
  assert.equal(runSlot(null, Date.parse("2026-08-22T07:30:00.000Z"), ANICCA_MAIN_SLOTS), "2026-08-22T07:00:00.000Z");
});
