"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { evaluateMentalTrigger } = require("../lib/mental-trigger.js");

const cases = fs.readFileSync(path.join(__dirname, "men-cases.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
const failures = [];
for (const testCase of cases) {
  const actual = evaluateMentalTrigger(testCase.input);
  if (JSON.stringify(actual) !== JSON.stringify(testCase.expected)) failures.push({ id: testCase.id, expected: testCase.expected, actual });
}
const passed = cases.length - failures.length;
console.log(`Mental trigger eval: ${passed}/${cases.length} (${(passed / cases.length * 100).toFixed(1)}%) judge=deterministic`);
for (const failure of failures) console.log(`FAIL ${failure.id}: expected=${JSON.stringify(failure.expected)} actual=${JSON.stringify(failure.actual)}`);
process.exitCode = failures.length ? 1 : 0;
