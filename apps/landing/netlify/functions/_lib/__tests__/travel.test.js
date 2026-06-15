// B-travel TDD — RED phase tests for travel-logic.js
// Pattern mirrors handler-telemetry.test.js (telemetry is the proven template).
// node --test netlify/functions/_lib/__tests__/travel.test.js

const { test } = require("node:test");
const assert = require("node:assert");

const {
  travelBlockTitle,
  buildTravelBlock,
  isTravelBlock,
  detectMissingTravelBlocks,
  secondsToIso,
} = require("../travel-logic");

// ── travelBlockTitle ──────────────────────────────────────────────────────────

test("travelBlockTitle returns '[Travel] <title>' for regular event", () => {
  assert.strictEqual(travelBlockTitle("歯科検診"), "[Travel] 歯科検診");
});

test("travelBlockTitle trims whitespace", () => {
  assert.strictEqual(travelBlockTitle("  Meeting  "), "[Travel] Meeting");
});

// ── isTravelBlock ─────────────────────────────────────────────────────────────

test("isTravelBlock returns true for auto-inserted blocks", () => {
  assert.strictEqual(isTravelBlock("[Travel] dentist"), true);
});

test("isTravelBlock returns false for regular events", () => {
  assert.strictEqual(isTravelBlock("dentist appointment"), false);
});

test("isTravelBlock returns false for empty string", () => {
  assert.strictEqual(isTravelBlock(""), false);
});

// ── secondsToIso ─────────────────────────────────────────────────────────────

test("secondsToIso converts unix seconds to ISO string", () => {
  // 1781568000 = 2026-06-16T00:00:00.000Z (verified: new Date(1781568000*1000).toISOString())
  const iso = secondsToIso(1781568000);
  assert.ok(typeof iso === "string");
  assert.ok(iso.includes("2026-06-16"));
});

// ── buildTravelBlock ──────────────────────────────────────────────────────────

test("buildTravelBlock returns a gcal-compatible event object", () => {
  const eventStart = 1750032000; // unix seconds
  const durationSec = 1200; // 20 min travel

  const block = buildTravelBlock({
    calendarId: "primary",
    eventTitle: "歯科検診",
    eventStart,
    durationSec,
  });

  assert.strictEqual(block.summary, "[Travel] 歯科検診");
  assert.strictEqual(block.calendarId, "primary");
  assert.ok(block.start && block.start.dateTime);
  assert.ok(block.end && block.end.dateTime);

  // block ends at eventStart
  const endDt = new Date(block.end.dateTime);
  assert.strictEqual(Math.round(endDt.getTime() / 1000), eventStart);

  // block starts durationSec before eventStart
  const startDt = new Date(block.start.dateTime);
  assert.strictEqual(Math.round(startDt.getTime() / 1000), eventStart - durationSec);
});

test("buildTravelBlock includes description with spec-required fields", () => {
  const block = buildTravelBlock({
    calendarId: "primary",
    eventTitle: "Team Sync",
    eventStart: 1750032000,
    durationSec: 900,
  });
  assert.ok(block.description.toLowerCase().includes("auto-inserted by anicca"));
  assert.ok(block.description.includes("Team Sync"));
});

test("buildTravelBlock uses colorId 7 (peacock) for visual distinction", () => {
  const block = buildTravelBlock({
    calendarId: "primary",
    eventTitle: "Meeting",
    eventStart: 1750032000,
    durationSec: 600,
  });
  assert.strictEqual(block.colorId, "7");
});

// ── detectMissingTravelBlocks ─────────────────────────────────────────────────

test("detectMissingTravelBlocks returns events missing a travel block", () => {
  const events = [
    { id: "ev1", summary: "歯科検診", start: { dateTime: "2026-06-16T10:00:00+09:00" } },
    { id: "ev2", summary: "[Travel] 歯科検診", start: { dateTime: "2026-06-16T09:40:00+09:00" } },
    { id: "ev3", summary: "Team Sync", start: { dateTime: "2026-06-16T14:00:00+09:00" } },
  ];

  const missing = detectMissingTravelBlocks(events);
  // ev1 has a travel block (ev2 covers it), ev3 does not
  const titles = missing.map((e) => e.summary);
  assert.ok(!titles.includes("歯科検診"), "ev1 should be covered by ev2");
  assert.ok(titles.includes("Team Sync"), "ev3 has no travel block");
});

test("detectMissingTravelBlocks skips events that are themselves travel blocks", () => {
  const events = [
    { id: "ev1", summary: "[Travel] Meeting", start: { dateTime: "2026-06-16T09:40:00+09:00" } },
    { id: "ev2", summary: "Meeting", start: { dateTime: "2026-06-16T10:00:00+09:00" } },
  ];
  const missing = detectMissingTravelBlocks(events);
  // [Travel] Meeting block exists for Meeting → not missing
  assert.strictEqual(missing.length, 0);
});

test("detectMissingTravelBlocks handles all-day events (no dateTime) gracefully", () => {
  const events = [
    { id: "ev1", summary: "Holiday", start: { date: "2026-06-16" } },
  ];
  // all-day events skip travel blocks (no departure time)
  const missing = detectMissingTravelBlocks(events);
  assert.strictEqual(missing.length, 0);
});
