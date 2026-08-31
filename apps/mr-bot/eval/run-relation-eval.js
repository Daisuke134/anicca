"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { detectRelationCadence } = require("../lib/relation-detector.js");

const DAY = 86400000;
const NOW = Date.parse("2026-07-27T00:00:00Z");
const cases = fs.readFileSync(path.join(__dirname, "relation-cases.jsonl"), "utf8")
  .trim().split("\n").map(JSON.parse);
const failures = [];

for (const testCase of cases) {
  const interactions = testCase.daysAgo.map((days, index) => ({
    interactionId: `${testCase.id}-${index}`,
    personKey: testCase.personKey,
    label: testCase.label,
    startMs: NOW - days * DAY,
    source: "calendar_1to1",
  }));
  const actual = detectRelationCadence({ nowMs: NOW, interactions });
  const first = actual.candidates[0];
  const observed = {
    count: actual.candidates.length,
    ...(first ? { decision: first.decision, reason: first.decisionReason } : {}),
  };
  if (JSON.stringify(observed) !== JSON.stringify(testCase.expected)) {
    failures.push({ id: testCase.id, expected: testCase.expected, actual: observed });
  }
}

const passed = cases.length - failures.length;
console.log(`Relations cadence eval: ${passed}/${cases.length} (${(passed / cases.length * 100).toFixed(1)}%) judge=deterministic`);
for (const failure of failures) {
  console.log(`FAIL ${failure.id}: expected=${JSON.stringify(failure.expected)} actual=${JSON.stringify(failure.actual)}`);
}
process.exitCode = failures.length ? 1 : 0;
