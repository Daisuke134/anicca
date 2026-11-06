"use strict";
// Maritime wake contract: T-10 (firm), T-5 (harsh), and event-start T-0 (harsh).
// Pins all three levels so a missing event-start wake is caught. Run: node --test test/wake-levels.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { WAKE_LEVELS } = require("../scheduler.js");

test("WAKE_LEVELS = exactly three levels: T-10 firm, T-5 harsh, T-0 harsh", () => {
  assert.deepStrictEqual(WAKE_LEVELS, [
    { min: 10, urgency: "firm" },
    { min: 5, urgency: "harsh" },
    { min: 0, urgency: "harsh" },
  ]);
});

test("WAKE_LEVELS: every urgency is valid (gentle|firm|harsh) and minutes are 5 apart, non-overlapping", () => {
  const valid = new Set(["gentle", "firm", "harsh"]);
  for (const l of WAKE_LEVELS) assert.ok(valid.has(l.urgency), `bad urgency ${l.urgency}`);
  const mins = WAKE_LEVELS.map((l) => l.min);
  assert.deepStrictEqual(mins, [...mins].sort((a, b) => b - a), "levels must be descending (latest = most urgent)");
  for (let i = 1; i < mins.length; i++) assert.ok(mins[i - 1] - mins[i] >= 5, "levels ≥5 min apart (no catch-window overlap)");
});
