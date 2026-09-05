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

test("a location explicitly marked online before a Peatix URL is online", () => {
  const result = interpretCalendarEvent({
    summary: "AI作曲体験",
    location: "オンライン: https://peatix.com/event/5156476",
    start: { dateTime: "2026-09-05T21:00:00+09:00" },
    end: { dateTime: "2026-09-05T22:00:00+09:00" },
  });
  assert.equal(result.decision, "online");
  assert.equal(result.travel, 0);
});
