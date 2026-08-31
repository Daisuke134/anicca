"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { evaluateJourney } = require("../eval/run-context-onboarding-discovery-eval.js");

test("CORE 8f drives the production context/onboarding/discovery journey at 100%", async () => {
  const outcome = await evaluateJourney();
  const failures = outcome.results.filter((item) => !item.pass).map((item) => ({
    id: item.id, expected: item.expected, actual: item.actual,
  }));
  assert.equal(outcome.passed, outcome.total, JSON.stringify(failures, null, 2));
});
