"use strict";
// 11a PHY-a contract: closed schemas + the two spec invariants — no fixed
// cycle imposed on anyone (no personal history → no detection, ever) and no
// medical diagnosis (the closed candidate schema has no field to carry one).
// The full decision matrix lives in eval/phy-cases.jsonl.

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateInput, detectUnmetCare } = require("./care-detector.js");

const DAY = 86400000;
const NOW = 1753344000000;

function input(overrides = {}) {
  return { nowMs: NOW, visits: [], intents: [], ...overrides };
}

test("schema: closed input keys and visit shape", () => {
  assert.doesNotThrow(() => validateInput(input()));
  assert.throws(() => validateInput({ ...input(), extra: 1 }), /unknown key/);
  assert.throws(() => validateInput(input({ visits: [{ startMs: 1, careType: "dental", note: "x" }] })), /unknown key: visit/);
  assert.throws(() => validateInput(input({ visits: [{ startMs: 1, careType: "" }] })), /careType/);
});

test("no fixed cycle: zero and single-visit histories never flag, at any elapsed time", () => {
  for (const yearsAgo of [1, 2, 5]) {
    const single = detectUnmetCare(input({ visits: [{ startMs: NOW - yearsAgo * 365 * DAY, careType: "dental" }] }));
    assert.deepEqual(single.candidates, [], `single visit ${yearsAgo}y ago must not flag`);
  }
  assert.deepEqual(detectUnmetCare(input()).candidates, []);
});

test("no diagnosis: candidates carry only visit-gap observation fields", () => {
  const out = detectUnmetCare(input({ visits: [
    { startMs: NOW - 660 * DAY, careType: "dental" },
    { startMs: NOW - 480 * DAY, careType: "dental" },
    { startMs: NOW - 300 * DAY, careType: "dental" },
  ] }));
  assert.equal(out.candidates.length, 1);
  assert.deepEqual(Object.keys(out.candidates[0]).sort(), [
    "careType", "lastVisitMs", "overdueDays", "personalIntervalDays", "reason",
  ]);
});

test("cadence is personal: identical elapsed time flags one user and not another", () => {
  const gapDays = 120;
  const shortCadence = detectUnmetCare(input({ visits: [
    { startMs: NOW - (gapDays + 90) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 45) * DAY, careType: "haircut" },
    { startMs: NOW - gapDays * DAY, careType: "haircut" },
  ] }));
  assert.equal(shortCadence.candidates.length, 1, "45-day-cadence user is overdue after 120 days");
  const longCadence = detectUnmetCare(input({ visits: [
    { startMs: NOW - (gapDays + 360) * DAY, careType: "haircut" },
    { startMs: NOW - (gapDays + 180) * DAY, careType: "haircut" },
    { startMs: NOW - gapDays * DAY, careType: "haircut" },
  ] }));
  assert.deepEqual(longCadence.candidates, [], "180-day-cadence user is fine after the same 120 days");
});
