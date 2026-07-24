"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { interpretCalendarEvent } = require("../lib/calendar-interpreter.js");

const file = path.join(__dirname, "calendar-cases.jsonl");
const cases = fs.readFileSync(file, "utf8").trim().split("\n").map(JSON.parse);

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((k) => [k, stable(value[k])]));
  return value;
}

function deterministicJudge(actual, expected) {
  if (expected && typeof expected === "object" && !Array.isArray(expected)) {
    return Object.keys(expected).every((key) => deterministicJudge(actual && actual[key], expected[key]));
  }
  return JSON.stringify(stable(actual)) === JSON.stringify(stable(expected));
}

async function llmJudge(actual, expected, apiKey) {
  const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: `Judge whether actual satisfies expected exactly. Return JSON {\"pass\":boolean}. Expected: ${JSON.stringify(expected)} Actual: ${JSON.stringify(actual)}` }] }],
      generationConfig: { responseMimeType: "application/json", temperature: 0 },
    }),
  });
  if (!response.ok) throw new Error(`Gemini judge HTTP ${response.status}`);
  const body = await response.json();
  return JSON.parse(body?.candidates?.[0]?.content?.parts?.[0]?.text || "{}").pass === true;
}

async function main() {
  const failures = [];
  let judge = process.env.GEMINI_API_KEY ? "gemini" : "deterministic";
  for (const testCase of cases) {
    const actual = interpretCalendarEvent(testCase.input, testCase.context || {});
    let pass;
    if (process.env.GEMINI_API_KEY) {
      try { pass = await llmJudge(actual, testCase.expected, process.env.GEMINI_API_KEY); }
      catch { judge = "deterministic-fallback"; pass = deterministicJudge(actual, testCase.expected); }
    } else pass = deterministicJudge(actual, testCase.expected);
    if (!pass) failures.push({ id: testCase.id, expected: testCase.expected, actual });
  }
  const passed = cases.length - failures.length;
  const score = (passed / cases.length * 100).toFixed(1);
  console.log(`Calendar eval: ${passed}/${cases.length} (${score}%) judge=${judge}`);
  for (const failure of failures) console.log(`FAIL ${failure.id}: expected=${JSON.stringify(failure.expected)} actual=${JSON.stringify(failure.actual)}`);
  process.exitCode = failures.length ? 1 : 0;
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
