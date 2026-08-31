"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { detectRelationCadence } = require("./relation-detector.js");

const DAY = 86400000;
const NOW = Date.parse("2026-07-27T00:00:00Z");

function interactions(personKey, label, daysAgo, source = "calendar_1to1") {
  return daysAgo.map((days, index) => ({
    interactionId: `${personKey}-${index}`,
    personKey,
    label,
    startMs: NOW - days * DAY,
    source,
  }));
}

test("stable personal monthly cadence that is overdue becomes actionable", () => {
  const result = detectRelationCadence({
    nowMs: NOW,
    interactions: interactions("p-mom", "母", [150, 120, 90, 60]),
  });
  assert.deepEqual(result.candidates, [{
    personKey: "p-mom",
    label: "母",
    source: "calendar_1to1",
    lastInteractionMs: NOW - 60 * DAY,
    personalIntervalDays: 30,
    daysSince: 60,
    overdueDays: 30,
    overdueRatio: 2,
    decision: "act",
    decisionReason: null,
  }]);
});

test("the same elapsed time stays silent when it is inside this person's own cadence", () => {
  const result = detectRelationCadence({
    nowMs: NOW,
    interactions: interactions("p-quarterly", "友人", [330, 240, 150, 60]),
  });
  assert.deepEqual(result.candidates, []);
});

test("zero, one, and two interactions never invent a cadence", () => {
  for (const daysAgo of [[], [400], [400, 200]]) {
    assert.deepEqual(detectRelationCadence({
      nowMs: NOW,
      interactions: interactions("p", "友人", daysAgo),
    }).candidates, []);
  }
});

test("three interactions can be observed but never acted on", () => {
  const [candidate] = detectRelationCadence({
    nowMs: NOW,
    interactions: interactions("p", "友人", [120, 90, 60]),
  }).candidates;
  assert.equal(candidate.decision, "observe");
  assert.equal(candidate.decisionReason, "insufficient-gaps");
});

test("a bursty, unstable interaction history remains observe-only", () => {
  const [candidate] = detectRelationCadence({
    nowMs: NOW,
    interactions: interactions("p", "友人", [500, 100, 95, 90, 60]),
  }).candidates;
  assert.equal(candidate.decision, "observe");
  assert.equal(candidate.decisionReason, "cadence-unstable");
});

test("one source event is counted once and candidates sort by largest overdue ratio", () => {
  const rows = [
    ...interactions("less", "Less", [150, 120, 90, 50]),
    ...interactions("more", "More", [150, 120, 90, 70]),
  ];
  rows.push({ ...rows[0] }); // duplicated provider row
  const result = detectRelationCadence({ nowMs: NOW, interactions: rows });
  assert.deepEqual(result.candidates.map((c) => c.personKey), ["more", "less"]);
  assert.equal(result.interactionCount, 8);
});

test("schema is closed and candidate output never carries email, phone, title, or location", () => {
  assert.throws(
    () => detectRelationCadence({ nowMs: NOW, interactions: [], email: "forbidden" }),
    /unknown key/,
  );
  const result = detectRelationCadence({
    nowMs: NOW,
    interactions: interactions("opaque", "表示名", [150, 120, 90, 60]),
  });
  const serialized = JSON.stringify(result);
  for (const forbidden of ["email", "phone", "title", "location"]) {
    assert.ok(!serialized.includes(forbidden));
  }
});

