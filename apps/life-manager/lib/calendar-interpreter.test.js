"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");

test("declined and tentative invitations never call", () => {
  for (const status of ["declined", "tentative"]) {
    assert.equal(interpretCalendarEvent({ status, start: { dateTime: "2026-07-22T10:00:00Z" } }).decision, "no_call");
  }
});

test("a recurring series answer is reused", () => {
  const result = interpretCalendarEvent({ recurringEventId: "r1", summary: "Lesson", start: { dateTime: "2026-07-22T10:00:00Z" } },
    { seriesAnswers: { r1: { decision: "offline", location: "School" } } });
  assert.deepEqual(result, { decision: "offline", travel: null, question: null, location: "School" });
});
