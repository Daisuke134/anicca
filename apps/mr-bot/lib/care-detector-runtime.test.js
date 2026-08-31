"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { detectCalendarCare } = require("./care-detector-runtime");

const DAY = 86_400_000;
const NOW = Date.parse("2026-07-24T00:00:00.000Z");

// CADENCE-1: two visits are one gap. The shaped receipt still carries the detection (the scan row
// stays honest about what was seen) but flags it observe_only — 11b/11c may not act on it.
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
      observe_only: true,
      decision_reason: "insufficient-gaps",
      source_provider_ids: ["provider-event-a", "provider-event-b"],
    }],
  });
  assert.doesNotMatch(JSON.stringify(receipt), /title|summary|location|diagnosis|lastVisitMs/);
});

test("a stable, overdue cadence shapes to an ACTIONABLE detection (observe_only false)", () => {
  const at = (days) => ({ id: `hc-${days}`, start: { dateTime: new Date(NOW - days * DAY).toISOString() } });
  const receipt = detectCalendarCare({
    nowMs: NOW,
    intents: [],
    sources: [{ careType: "haircut", events: [at(230), at(190), at(156), at(110), at(70)] }],
  });
  assert.equal(receipt.candidates.length, 1);
  assert.equal(receipt.candidates[0].observe_only, false);
  assert.equal(receipt.candidates[0].decision_reason, null);
  assert.equal(receipt.candidates[0].personal_interval_days, 40);
});

test("the bimodal burst that produced the first production row shapes to observe_only", () => {
  // gaps 47.0 / 5.7 / 8.5 / 419 / 3.2 days — median 9, MAD 5.3 > 4.25, and 419 ≫ 2.5×9.
  const gapDays = [47.02, 5.75, 8.52, 419.0, 3.25];
  const offsets = [0];
  for (const gap of gapDays) offsets.push(offsets[offsets.length - 1] + gap);
  const span = offsets[offsets.length - 1];
  const events = offsets.map((o, i) => ({
    id: `burst-${i}`,
    start: { dateTime: new Date(NOW - (span - o + 58) * DAY).toISOString() },
  }));
  const receipt = detectCalendarCare({ nowMs: NOW, intents: [], sources: [{ careType: "clinic", events }] });
  assert.equal(receipt.candidates.length, 1, "recorded, not dropped");
  assert.equal(receipt.candidates[0].observe_only, true);
  assert.equal(receipt.candidates[0].decision_reason, "cadence-unstable");
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
