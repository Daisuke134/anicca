"use strict";
// REQ-29 (Dais 2026-06-25): TWO escalating wake calls only — T-10 (firm) + T-5 (harsh) before DEPARTURE.
// Pins the levels so a revert to the old T-15/10/5 is caught. Run: node --test test/wake-levels.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { WAKE_LEVELS } = require("../scheduler.js");

test("WAKE_LEVELS = exactly two calls: T-10 firm, T-5 harsh (no T-15)", () => {
  assert.deepStrictEqual(WAKE_LEVELS, [
    { min: 10, urgency: "firm" },
    { min: 5, urgency: "harsh" },
  ]);
});

test("WAKE_LEVELS: every urgency is valid (gentle|firm|harsh) and minutes are 5 apart, non-overlapping", () => {
  const valid = new Set(["gentle", "firm", "harsh"]);
  for (const l of WAKE_LEVELS) assert.ok(valid.has(l.urgency), `bad urgency ${l.urgency}`);
  const mins = WAKE_LEVELS.map((l) => l.min);
  assert.deepStrictEqual(mins, [...mins].sort((a, b) => b - a), "levels must be descending (latest = most urgent)");
  for (let i = 1; i < mins.length; i++) assert.ok(mins[i - 1] - mins[i] >= 5, "levels ≥5 min apart (no catch-window overlap)");
});
