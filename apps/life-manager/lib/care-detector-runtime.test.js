"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { detectCalendarCare } = require("./care-detector-runtime");

const DAY = 86_400_000;
const NOW = Date.parse("2026-07-24T00:00:00.000Z");

test("real-provider-shaped events feed the existing detector without title, location, or diagnosis", () => {
  const receipt = detectCalendarCare({
    nowMs: NOW,
    intents: [],
    sources: [{
      careType: "clinic",
      events: [
        { id: "provider-event-a", start: { dateTime: new Date(NOW - 478 * DAY).toISOString() } },
        { id: "provider-event-b", start: { dateTime: new Date(NOW - 469 * DAY).toISOString() } },
      ],
    }],
  });

  assert.deepEqual(receipt, {
    schema_version: 1,
    real_event_count: 2,
    candidates: [{
      care_type: "clinic",
      reason: "personal-cadence-overdue",
      personal_interval_days: 9,
      overdue_days: 460,
      source_provider_ids: ["provider-event-a", "provider-event-b"],
    }],
  });
  assert.doesNotMatch(JSON.stringify(receipt), /title|summary|location|diagnosis|lastVisitMs/);
});

test("duplicate provider events across searches count once and a single real visit never flags", () => {
  const receipt = detectCalendarCare({
    nowMs: NOW,
    intents: [],
    sources: [
      { careType: "dental", events: [{ id: "same", start: { date: "2025-01-01" } }] },
      { careType: "dental", events: [{ id: "same", start: { date: "2025-01-01" } }] },
    ],
  });
  assert.equal(receipt.real_event_count, 1);
  assert.deepEqual(receipt.candidates, []);
});

test("malformed or future provider rows are discarded instead of fabricating care history", () => {
  const receipt = detectCalendarCare({
    nowMs: NOW,
    intents: [],
    sources: [{
      careType: "clinic",
      events: [
        { id: "missing-start" },
        { id: "future", start: { dateTime: new Date(NOW + DAY).toISOString() } },
        { id: "", start: { date: "2025-01-01" } },
      ],
    }],
  });
  assert.deepEqual(receipt, { schema_version: 1, real_event_count: 0, candidates: [] });
});
