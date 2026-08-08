"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertGeneratedEnglish,
  assertNoClientAuthority,
  assertOpaque,
  assertIso,
} = require("./mobile-contract-support.js");

const TERMINAL_STATES = [
  "route_ready", "needs_information", "no_upcoming_event", "route_unavailable", "failed",
];

test("direct next-event analysis freezes exactly five terminal states", () => {
  const states = TERMINAL_STATES.map((status) => fixture(`analysis-${status}.json`));
  assert.deepEqual(states.map((item) => item.status).sort(), [...TERMINAL_STATES].sort());

  for (const result of states) {
    assert.deepEqual(Object.keys(result).sort(), ["analysisId", "message", "nextCursor", "status"].sort());
    assertOpaque(result.analysisId, `${result.status} analysis id`);
    assertOpaque(result.nextCursor, `${result.status} next cursor`, /^cursor:v1:[A-Za-z0-9_-]{8,}$/u);
    assert.equal(result.message && typeof result.message, "object");
    assertOpaque(result.message.id, `${result.status} message id`);
    assertIso(result.message.createdAt, `${result.status} message createdAt`);
    assert.equal(result.message.locale, "en");
    assertGeneratedEnglish(result, `${result.status} analysis`);
    assertNoClientAuthority(result, `${result.status} analysis`);
  }
});

test("terminal analysis fixtures expose route/question only for the matching state", () => {
  const ready = fixture("analysis-route_ready.json");
  const question = fixture("analysis-needs_information.json");
  const noEvent = fixture("analysis-no_upcoming_event.json");
  const unavailable = fixture("analysis-route_unavailable.json");
  const failed = fixture("analysis-failed.json");

  assert.equal(ready.message.type, "route");
  assert.equal(ready.message.route.status, "route_ready");
  assert.equal(ready.message.question, null);
  assert.equal(question.message.type, "question");
  assert.equal(question.message.route, null);
  assert.equal(typeof question.message.question.id, "string");
  assert.equal(typeof question.message.question.prompt, "string");
  for (const result of [noEvent, unavailable, failed]) {
    assert.equal(result.message.route, null, `${result.status} cannot carry a route`);
  }
  assert.equal(unavailable.message.type, "route_unavailable");
  assert.equal(failed.message.type, "system");
});
