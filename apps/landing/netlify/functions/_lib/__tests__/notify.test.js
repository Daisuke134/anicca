// B-notify TDD — tests for notify-logic.js
// spec27 WF-B B-notify: email-only approval gate.
// node --test netlify/functions/_lib/__tests__/notify.test.js

const { test } = require("node:test");
const assert = require("node:assert");

const {
  isLateRisk,
  detectLateRiskEvents,
  buildApprovalEmail,
  buildAttendeeDraft,
  extractApproval,
  isTravelBlock,
} = require("../notify-logic");

// ── isTravelBlock ─────────────────────────────────────────────────────────────

test("isTravelBlock returns true for [Travel] prefixed events", () => {
  assert.strictEqual(isTravelBlock("[Travel] dentist"), true);
});

test("isTravelBlock returns false for normal events", () => {
  assert.strictEqual(isTravelBlock("dentist appointment"), false);
});

// ── isLateRisk ────────────────────────────────────────────────────────────────

test("isLateRisk returns true when travel block has already started (nowMs > travelStartMs)", () => {
  // travel block starts at T, event at T+1800s, now is T+300s → late risk
  const travelStartMs = Date.now() - 300_000; // 5 min ago
  const result = isLateRisk({ travelStartMs, nowMs: Date.now() });
  assert.strictEqual(result, true);
});

test("isLateRisk returns false when travel block starts in the future", () => {
  const travelStartMs = Date.now() + 600_000; // 10 min from now
  const result = isLateRisk({ travelStartMs, nowMs: Date.now() });
  assert.strictEqual(result, false);
});

test("isLateRisk returns false when exactly at travel start (boundary)", () => {
  const travelStartMs = Date.now();
  const result = isLateRisk({ travelStartMs, nowMs: travelStartMs });
  assert.strictEqual(result, false);
});

// ── detectLateRiskEvents ──────────────────────────────────────────────────────

test("detectLateRiskEvents pairs travel blocks with target events and flags late risk", () => {
  const nowMs = Date.now();
  const travelStartMs = nowMs - 300_000; // 5 min ago → late risk
  const eventStartMs = nowMs + 300_000;  // 5 min from now

  const travelStartIso = new Date(travelStartMs).toISOString();
  const eventStartIso = new Date(eventStartMs).toISOString();

  const events = [
    {
      id: "ev-travel-1",
      summary: "[Travel] Team Sync",
      start: { dateTime: travelStartIso },
      end:   { dateTime: new Date(nowMs).toISOString() },
    },
    {
      id: "ev-1",
      summary: "Team Sync",
      start: { dateTime: eventStartIso },
      end:   { dateTime: new Date(eventStartMs + 3_600_000).toISOString() },
      attendees: [{ email: "boss@example.com" }],
    },
  ];

  const risks = detectLateRiskEvents(events, nowMs);
  assert.strictEqual(risks.length, 1);
  assert.strictEqual(risks[0].event.summary, "Team Sync");
  assert.strictEqual(risks[0].isLate, true);
});

test("detectLateRiskEvents returns empty array when travel block has not started yet", () => {
  const nowMs = Date.now();
  const travelStartMs = nowMs + 600_000; // future
  const eventStartMs = nowMs + 1_800_000;

  const events = [
    {
      id: "ev-travel-2",
      summary: "[Travel] Lunch",
      start: { dateTime: new Date(travelStartMs).toISOString() },
      end:   { dateTime: new Date(eventStartMs).toISOString() },
    },
    {
      id: "ev-2",
      summary: "Lunch",
      start: { dateTime: new Date(eventStartMs).toISOString() },
      end:   { dateTime: new Date(eventStartMs + 3_600_000).toISOString() },
      attendees: [],
    },
  ];

  const risks = detectLateRiskEvents(events, nowMs);
  assert.strictEqual(risks.length, 0);
});

test("detectLateRiskEvents skips all-day events (no dateTime)", () => {
  const nowMs = Date.now();
  const events = [
    { id: "ev-3", summary: "Holiday", start: { date: "2026-06-17" }, attendees: [] },
  ];
  const risks = detectLateRiskEvents(events, nowMs);
  assert.strictEqual(risks.length, 0);
});

test("detectLateRiskEvents only flags events with matching [Travel] block", () => {
  const nowMs = Date.now();
  const pastMs = nowMs - 600_000;
  const futureMs = nowMs + 1_800_000;

  // Event with NO [Travel] block — should NOT appear in risks
  const events = [
    {
      id: "ev-4",
      summary: "Doctor",
      start: { dateTime: new Date(futureMs).toISOString() },
      end:   { dateTime: new Date(futureMs + 3_600_000).toISOString() },
      attendees: [{ email: "clinic@example.com" }],
    },
  ];

  const risks = detectLateRiskEvents(events, nowMs);
  assert.strictEqual(risks.length, 0);
});

// ── buildApprovalEmail ────────────────────────────────────────────────────────

test("buildApprovalEmail returns object with to, subject, body fields", () => {
  const result = buildApprovalEmail({
    ownerEmail: "daisuke@example.com",
    eventSummary: "Team Sync",
    attendees: [{ email: "boss@example.com" }],
    draftBody: "I'll be 10 minutes late.",
    draftId: "draft-123",
  });

  assert.ok(typeof result.to === "string");
  assert.ok(typeof result.subject === "string");
  assert.ok(typeof result.body === "string");

  // Must be sent TO the owner (Dais), not to attendees
  assert.strictEqual(result.to, "daisuke@example.com");

  // Body must contain the draft message
  assert.ok(result.body.includes("I'll be 10 minutes late."));

  // Body must contain the attendee info
  assert.ok(result.body.includes("boss@example.com"));

  // Body must explain the approval flow
  assert.ok(result.body.toLowerCase().includes("ok"));
});

test("buildApprovalEmail subject contains event name", () => {
  const result = buildApprovalEmail({
    ownerEmail: "owner@example.com",
    eventSummary: "歯科検診",
    attendees: [],
    draftBody: "遅れます",
    draftId: "draft-456",
  });
  assert.ok(result.subject.includes("歯科検診"));
});

test("buildApprovalEmail works with zero attendees (unknown contact scenario)", () => {
  const result = buildApprovalEmail({
    ownerEmail: "owner@example.com",
    eventSummary: "Solo event",
    attendees: [],
    draftBody: "遅れます",
    draftId: "draft-789",
  });
  assert.ok(result.body.includes("遅れます"));
});

// ── buildAttendeeDraft ────────────────────────────────────────────────────────

test("buildAttendeeDraft returns a draft message body string", () => {
  const result = buildAttendeeDraft({
    eventSummary: "Team Sync",
    minutesLate: 10,
  });
  assert.ok(typeof result === "string");
  assert.ok(result.length > 0);
  assert.ok(result.includes("10"));
});

test("buildAttendeeDraft includes event name", () => {
  const result = buildAttendeeDraft({ eventSummary: "Meeting with Kato", minutesLate: 5 });
  assert.ok(result.includes("Meeting with Kato"));
});

// ── extractApproval ───────────────────────────────────────────────────────────

test("extractApproval returns true for 'OK' reply (case-insensitive)", () => {
  assert.strictEqual(extractApproval("OK"), true);
  assert.strictEqual(extractApproval("ok"), true);
  assert.strictEqual(extractApproval("Ok!"), true);
  assert.strictEqual(extractApproval("  OK  "), true);
});

test("extractApproval returns true for 'はい' reply", () => {
  assert.strictEqual(extractApproval("はい"), true);
  assert.strictEqual(extractApproval("はい、送ってください"), true);
});

test("extractApproval returns false for unrecognised reply", () => {
  assert.strictEqual(extractApproval("no"), false);
  assert.strictEqual(extractApproval("wait"), false);
  assert.strictEqual(extractApproval(""), false);
  assert.strictEqual(extractApproval("send tomorrow instead"), false);
});
