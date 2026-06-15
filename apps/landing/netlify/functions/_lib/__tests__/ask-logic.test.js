// ask-logic.test.js — unit tests for the B-ask pure-logic module.
//
// Covers every exported function in ask-logic.js using TDD.
// No network I/O. Uses node:test + node:assert.
//
// Run: node --test apps/landing/netlify/functions/_lib/__tests__/ask-logic.test.js

"use strict";

const { test } = require("node:test");
const assert = require("node:assert");

const {
  needsLocationAsk,
  detectMissingLocations,
  buildQuestionBody,
  buildQuestionSubject,
  parseLocationFromReply,
  buildLocationPatch,
  buildAskPendingPatch,
  ASK_PREFIX,
  AGENTMAIL_PENDING_PROP,
  AGENTMAIL_QUESTION_ID_PROP,
} = require("../ask-logic");

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeTimedEvent(id, summary, overrides = {}) {
  return {
    id,
    summary,
    start: { dateTime: "2026-06-17T10:00:00+09:00" },
    end: { dateTime: "2026-06-17T11:00:00+09:00" },
    ...overrides,
  };
}

// ── needsLocationAsk ───────────────────────────────────────────────────────────

test("needsLocationAsk: returns true for timed event with no location", () => {
  const ev = makeTimedEvent("ev1", "歯科検診");
  assert.strictEqual(needsLocationAsk(ev), true);
});

test("needsLocationAsk: returns false for all-day event (no start.dateTime)", () => {
  const ev = { id: "ev2", summary: "祝日", start: { date: "2026-06-17" }, end: { date: "2026-06-17" } };
  assert.strictEqual(needsLocationAsk(ev), false);
});

test("needsLocationAsk: returns false when event already has a location", () => {
  const ev = makeTimedEvent("ev3", "歯科検診", { location: "伊藤歯科クリニック" });
  assert.strictEqual(needsLocationAsk(ev), false);
});

test("needsLocationAsk: returns false for [Travel] prefixed events", () => {
  const ev = makeTimedEvent("ev4", "[Travel] 歯科検診");
  assert.strictEqual(needsLocationAsk(ev), false);
});

test("needsLocationAsk: returns false for [Ask] prefixed events", () => {
  const ev = makeTimedEvent("ev5", "[Ask] 場所を教えて — 会議");
  assert.strictEqual(needsLocationAsk(ev), false);
});

test("needsLocationAsk: returns false when ask is already pending (extendedProperties)", () => {
  const ev = makeTimedEvent("ev6", "Team Meeting", {
    extendedProperties: { private: { anicca_ask_pending: "true" } },
  });
  assert.strictEqual(needsLocationAsk(ev), false);
});

test("needsLocationAsk: returns false for null/undefined input", () => {
  assert.strictEqual(needsLocationAsk(null), false);
  assert.strictEqual(needsLocationAsk(undefined), false);
});

test("needsLocationAsk: returns false for event with empty location string", () => {
  // Empty string should be treated as missing → true
  const ev = makeTimedEvent("ev7", "Morning Standup", { location: "" });
  // empty string → still needs ask
  assert.strictEqual(needsLocationAsk(ev), true);
});

// ── detectMissingLocations ─────────────────────────────────────────────────────

test("detectMissingLocations: returns only events missing location", () => {
  const events = [
    makeTimedEvent("ev1", "歯科検診"), // no location → needs ask
    makeTimedEvent("ev2", "Lunch", { location: "渋谷ヒカリエ" }), // has location
    makeTimedEvent("ev3", "[Travel] 歯科検診"), // travel block
    makeTimedEvent("ev4", "Team Sync"), // no location → needs ask
    { id: "ev5", summary: "Holiday", start: { date: "2026-06-17" }, end: { date: "2026-06-17" } }, // all-day
  ];
  const result = detectMissingLocations(events);
  assert.strictEqual(result.length, 2);
  assert.ok(result.some((e) => e.id === "ev1"));
  assert.ok(result.some((e) => e.id === "ev4"));
});

test("detectMissingLocations: returns empty array for non-array input", () => {
  assert.deepStrictEqual(detectMissingLocations(null), []);
  assert.deepStrictEqual(detectMissingLocations(undefined), []);
  assert.deepStrictEqual(detectMissingLocations("not an array"), []);
});

test("detectMissingLocations: returns empty array when all events have locations", () => {
  const events = [
    makeTimedEvent("ev1", "Meeting", { location: "Tokyo" }),
    makeTimedEvent("ev2", "Lunch", { location: "Shibuya" }),
  ];
  assert.deepStrictEqual(detectMissingLocations(events), []);
});

// ── buildQuestionBody ──────────────────────────────────────────────────────────

test("buildQuestionBody: includes event title and event ID", () => {
  const ev = makeTimedEvent("ev-abc-123", "歯科検診");
  const body = buildQuestionBody(ev);
  assert.ok(body.includes("歯科検診"), "body must include event title");
  assert.ok(body.includes("ev-abc-123"), "body must include event ID for webhook matching");
});

test("buildQuestionBody: includes location request phrasing", () => {
  const ev = makeTimedEvent("ev1", "Morning Meeting");
  const body = buildQuestionBody(ev);
  assert.ok(body.includes("場所"), "body must ask about location");
  assert.ok(body.includes("返信"), "body must ask user to reply");
});

test("buildQuestionBody: handles event with no title gracefully", () => {
  const ev = makeTimedEvent("ev1", "");
  const body = buildQuestionBody(ev);
  assert.ok(body.includes("(no title)"), "body must handle empty title");
});

// ── buildQuestionSubject ───────────────────────────────────────────────────────

test("buildQuestionSubject: starts with [Ask] prefix", () => {
  const ev = makeTimedEvent("ev1", "歯科検診");
  const subject = buildQuestionSubject(ev);
  assert.ok(subject.startsWith(ASK_PREFIX), `subject must start with "${ASK_PREFIX}"`);
});

test("buildQuestionSubject: includes event title", () => {
  const ev = makeTimedEvent("ev1", "Team Standup");
  const subject = buildQuestionSubject(ev);
  assert.ok(subject.includes("Team Standup"), "subject must include event title");
});

// ── parseLocationFromReply ─────────────────────────────────────────────────────

test("parseLocationFromReply: extracts plain location from first line", () => {
  const body = "新宿駅南口";
  assert.strictEqual(parseLocationFromReply(body), "新宿駅南口");
});

test("parseLocationFromReply: strips 場所: prefix", () => {
  const body = "場所: 渋谷ヒカリエ 8F";
  assert.strictEqual(parseLocationFromReply(body), "渋谷ヒカリエ 8F");
});

test("parseLocationFromReply: strips 場所： (full-width colon) prefix", () => {
  const body = "場所：東京ビッグサイト";
  assert.strictEqual(parseLocationFromReply(body), "東京ビッグサイト");
});

test("parseLocationFromReply: strips → prefix", () => {
  const body = "→ 東京ビッグサイト";
  assert.strictEqual(parseLocationFromReply(body), "東京ビッグサイト");
});

test("parseLocationFromReply: ignores quoted original lines starting with >", () => {
  const body = "> Anicca より確認です。\n> 予定「歯科検診」...\n信濃町駅";
  assert.strictEqual(parseLocationFromReply(body), "信濃町駅");
});

test("parseLocationFromReply: ignores Event ID: metadata line", () => {
  const body = "Event ID: ev-123\n東京駅丸の内口";
  assert.strictEqual(parseLocationFromReply(body), "東京駅丸の内口");
});

test("parseLocationFromReply: returns null for empty body", () => {
  assert.strictEqual(parseLocationFromReply(""), null);
  assert.strictEqual(parseLocationFromReply(null), null);
  assert.strictEqual(parseLocationFromReply(undefined), null);
});

test("parseLocationFromReply: returns null when reply contains only quoted lines", () => {
  const body = "> original message\n> another quoted line";
  assert.strictEqual(parseLocationFromReply(body), null);
});

// ── buildLocationPatch ─────────────────────────────────────────────────────────

test("buildLocationPatch: sets location field", () => {
  const patch = buildLocationPatch("新宿駅南口", {});
  assert.strictEqual(patch.location, "新宿駅南口");
});

test("buildLocationPatch: removes anicca_ask_pending from extendedProperties", () => {
  const existing = {
    extendedProperties: {
      private: {
        anicca_ask_pending: "true",
        anicca_ask_question_id: "msg-abc",
        other_key: "keep",
      },
    },
  };
  const patch = buildLocationPatch("渋谷ヒカリエ", existing);
  assert.ok(
    patch.extendedProperties.private[AGENTMAIL_PENDING_PROP] === undefined,
    "pending flag must be removed"
  );
  assert.ok(
    patch.extendedProperties.private[AGENTMAIL_QUESTION_ID_PROP] === undefined,
    "question_id must be removed"
  );
  // Other keys must be preserved
  assert.strictEqual(patch.extendedProperties.private.other_key, "keep");
});

test("buildLocationPatch: works when event has no extendedProperties", () => {
  const patch = buildLocationPatch("Tokyo", {});
  assert.strictEqual(patch.location, "Tokyo");
  assert.deepStrictEqual(patch.extendedProperties.private, {});
});

// ── buildAskPendingPatch ───────────────────────────────────────────────────────

test("buildAskPendingPatch: sets anicca_ask_pending=true", () => {
  const patch = buildAskPendingPatch("msg-123", {});
  assert.strictEqual(patch.extendedProperties.private[AGENTMAIL_PENDING_PROP], "true");
});

test("buildAskPendingPatch: sets anicca_ask_question_id", () => {
  const patch = buildAskPendingPatch("msg-xyz-456", {});
  assert.strictEqual(patch.extendedProperties.private[AGENTMAIL_QUESTION_ID_PROP], "msg-xyz-456");
});

test("buildAskPendingPatch: preserves existing extendedProperties", () => {
  const existing = {
    extendedProperties: { private: { anicca_travel_block: "true" } },
  };
  const patch = buildAskPendingPatch("msg-1", existing);
  assert.strictEqual(patch.extendedProperties.private.anicca_travel_block, "true");
  assert.strictEqual(patch.extendedProperties.private[AGENTMAIL_PENDING_PROP], "true");
});

test("buildAskPendingPatch: works when event has no extendedProperties", () => {
  const patch = buildAskPendingPatch("msg-1", {});
  assert.strictEqual(patch.extendedProperties.private[AGENTMAIL_PENDING_PROP], "true");
});
