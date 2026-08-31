"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { inferEventTalkOpportunity } = require("../lib/event-talk-opportunity.js");

function expectedMatch(actual, expected) {
  return Object.entries(expected).every(([key, value]) => (
    JSON.stringify(actual && actual[key]) === JSON.stringify(value)
  ));
}

async function main() {
  const apiKey = String(process.env.GEMINI_API_KEY || "").trim();
  if (!apiKey) throw new Error("GEMINI_API_KEY is required for Connector talk eval");
  const file = path.join(__dirname, "connector-talk-cases.jsonl");
  const cases = fs.readFileSync(file, "utf8").trim().split("\n").map(JSON.parse);
  const failures = [];
  for (const testCase of cases) {
    try {
      const actual = await inferEventTalkOpportunity(testCase.input, { apiKey });
      if (!expectedMatch(actual, testCase.expected)) {
        failures.push({ id: testCase.id, expected: testCase.expected, actual });
      }
    } catch (error) {
      failures.push({ id: testCase.id, error: String(error && error.message || error) });
    }
  }
  const passed = cases.length - failures.length;
  const score = (passed / cases.length * 100).toFixed(1);
  process.stdout.write(`Connector talk eval: ${passed}/${cases.length} (${score}%) model=gemini-2.5-flash judge=deterministic\n`);
  for (const failure of failures) process.stdout.write(`FAIL ${failure.id}: ${JSON.stringify(failure)}\n`);
  process.exitCode = failures.length ? 1 : 0;
}

main().catch((error) => {
  process.stderr.write(`${String(error && error.message || error)}\n`);
  process.exitCode = 1;
});
