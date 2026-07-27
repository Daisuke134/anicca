"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  extractCalendarInteractions,
  personKeyForEmail,
} = require("./relation-calendar.js");

const NOW = Date.parse("2026-07-27T00:00:00Z");
const SECRET = "test-secret-at-least-32-bytes-long";

function event(overrides = {}) {
  return {
    id: "event-1",
    startMs: NOW - 30 * 86400000,
    endMs: NOW - 30 * 86400000 + 3600000,
    attendees: [
      { email: "owner@example.com", self: true, responseStatus: "accepted" },
      { email: "mother@example.com", displayName: "母", responseStatus: "accepted" },
    ],
    organizer: { email: "owner@example.com", self: true },
    ...overrides,
  };
}

test("extracts a timed one-to-one event with a provider display name", () => {
  assert.deepEqual(extractCalendarInteractions([event()], { secret: SECRET }), [{
    interactionId: "event-1",
    personKey: personKeyForEmail("mother@example.com", SECRET),
    label: "母",
    startMs: NOW - 30 * 86400000,
    source: "calendar_1to1",
  }]);
});

test("requires exactly one accepted external human", () => {
  const extra = { email: "friend@example.com", displayName: "友人", responseStatus: "accepted" };
  assert.deepEqual(extractCalendarInteractions([event({
    attendees: [...event().attendees, extra],
  })], { secret: SECRET }), []);
  assert.deepEqual(extractCalendarInteractions([event({
    attendees: [event().attendees[0]],
  })], { secret: SECRET }), []);
});

test("declined participants and resources do not become people", () => {
  const rows = event().attendees.concat([
    { email: "room@example.com", displayName: "Room", resource: true },
    { email: "declined@example.com", displayName: "Declined", responseStatus: "declined" },
  ]);
  assert.equal(extractCalendarInteractions([event({ attendees: rows })], { secret: SECRET }).length, 1);
});

test("never infers a name from email or event title", () => {
  assert.deepEqual(extractCalendarInteractions([event({
    summary: "Dinner with Mother",
    attendees: [
      event().attendees[0],
      { email: "mother@example.com", responseStatus: "accepted" },
    ],
  })], { secret: SECRET }), []);
});

test("rejects all-day, too-short, and implausibly long meetings", () => {
  assert.deepEqual(extractCalendarInteractions([event({ endMs: null })], { secret: SECRET }), []);
  assert.deepEqual(extractCalendarInteractions([event({ endMs: event().startMs + 9 * 60000 })], { secret: SECRET }), []);
  assert.deepEqual(extractCalendarInteractions([event({ endMs: event().startMs + 6 * 3600000 + 1 })], { secret: SECRET }), []);
});

test("output is PII-minimal and identity is a keyed stable digest", () => {
  const first = extractCalendarInteractions([event()], { secret: SECRET })[0];
  const second = extractCalendarInteractions([event({ id: "event-2" })], { secret: SECRET })[0];
  assert.equal(first.personKey, second.personKey);
  assert.match(first.personKey, /^rel_[a-f0-9]{32}$/);
  const serialized = JSON.stringify(first);
  for (const forbidden of ["mother@example.com", "summary", "location", "phone"]) {
    assert.ok(!serialized.includes(forbidden));
  }
});

test("fails closed without an HMAC secret or with malformed display names", () => {
  assert.throws(() => extractCalendarInteractions([event()], { secret: "" }), /secret/i);
  for (const label of ["mother@example.com", "+81 90-1234-5678", "https://example.com"]) {
    assert.deepEqual(extractCalendarInteractions([event({
      attendees: [
        event().attendees[0],
        { email: "mother@example.com", displayName: label, responseStatus: "accepted" },
      ],
    })], { secret: SECRET }), []);
  }
});
