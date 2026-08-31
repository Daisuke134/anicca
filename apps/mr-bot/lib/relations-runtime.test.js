"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { relationsUserOnce } = require("./relations-runtime.js");

const DAY = 86400000;
const NOW = Date.parse("2026-07-27T09:35:00Z"); // 18:35 JST
const USER = {
  uid: "user-1",
  telegram_chat_id: "chat-1",
  notifications_enabled: true,
  call_time_zone: "Asia/Tokyo",
};

function calendarHistory() {
  return [150, 120, 90, 60].map((days, index) => ({
    id: `event-${index}`,
    summary: `private-${index}`,
    location: "private-place",
    startMs: NOW - days * DAY,
    endMs: NOW - days * DAY + 3600000,
    attendees: [
      { email: "owner@example.com", self: true, responseStatus: "accepted" },
      { email: "mother@example.com", displayName: "母", responseStatus: "accepted" },
    ],
  }));
}

function deps(overrides = {}) {
  const rows = [];
  const sends = [];
  const base = {
    supaUrl: "https://supa.example",
    supaKey: "service-key",
    hashSecret: "test-secret-at-least-32-bytes-long",
    fetchHistory: async () => calendarHistory(),
    scanExists: async () => false,
    readAttemptState: async () => ({ lastAttemptMs: null }),
    appendRow: async (row) => { rows.push(row); return true; },
    readMentalSendState: async () => ({ sentTodayCount: 0, lastSentMs: null }),
    getLocationState: async () => "still",
    sendMessage: async (_token, _chatId, text) => {
      sends.push(text);
      return { ok: true, result: { message_id: 42 } };
    },
    recordMentalSend: async () => true,
    events: [],
    tzOffsetH: 9,
  };
  return { options: { ...base, ...overrides }, rows, sends };
}

test("stable overdue cadence claims, sends one gentle suggestion, and records delivery", async () => {
  const fixture = deps();
  const result = await relationsUserOnce(USER, NOW, fixture.options);
  assert.equal(result.status, "suggested");
  assert.equal(result.telegramMessageId, 42);
  assert.equal(fixture.sends.length, 1);
  assert.match(fixture.sends[0], /母/);
  assert.match(fixture.sends[0], /60日/);
  assert.deepEqual(fixture.rows.map((row) => row.kind), [
    "scan", "suggestion_attempt", "delivery",
  ]);
});

test("durable rows never contain names, email, title, location, or message copy", async () => {
  const fixture = deps();
  await relationsUserOnce(USER, NOW, fixture.options);
  const persisted = JSON.stringify(fixture.rows);
  for (const forbidden of [
    "母", "mother@example.com", "private-", "private-place", "message_text",
    "カレンダーでは",
  ]) {
    assert.ok(!persisted.includes(forbidden), `must not persist ${forbidden}`);
  }
});

test("missing provider display names abstain instead of inferring identity", async () => {
  const history = calendarHistory().map((row) => ({
    ...row,
    attendees: row.attendees.map((person) => {
      const copy = { ...person };
      delete copy.displayName;
      return copy;
    }),
  }));
  const fixture = deps({ fetchHistory: async () => history });
  const result = await relationsUserOnce(USER, NOW, fixture.options);
  assert.equal(result.status, "abstained");
  assert.equal(fixture.sends.length, 0);
  assert.deepEqual(fixture.rows.map((row) => row.kind), ["scan"]);
});

test("unknown timezone, moving/unknown location, active event, mental cap, and 2h spacing suppress", async () => {
  const cases = [
    { tzOffsetH: null },
    { getLocationState: async () => "moving" },
    { getLocationState: async () => "unknown" },
    { events: [{ startMs: NOW - 1000, endMs: NOW + 1000 }] },
    { readMentalSendState: async () => ({ sentTodayCount: 3, lastSentMs: null }) },
    { readMentalSendState: async () => ({ sentTodayCount: 1, lastSentMs: NOW - 60000 }) },
  ];
  for (const override of cases) {
    const fixture = deps(override);
    const result = await relationsUserOnce(
      override.tzOffsetH === null ? { ...USER, call_time_zone: null } : USER,
      NOW,
      fixture.options,
    );
    assert.notEqual(result.status, "suggested");
    assert.equal(fixture.sends.length, 0);
  }
});

test("a trailing-seven-day attempt suppresses a new suggestion", async () => {
  const fixture = deps({
    readAttemptState: async () => ({ lastAttemptMs: NOW - 6 * DAY }),
  });
  const result = await relationsUserOnce(USER, NOW, fixture.options);
  assert.equal(result.status, "suppressed");
  assert.equal(result.reason, "weekly-spacing");
  assert.equal(fixture.sends.length, 0);
});

test("claim is before send and a lost claim never sends", async () => {
  const fixture = deps({
    appendRow: async (row) => row.kind !== "suggestion_attempt",
  });
  const result = await relationsUserOnce(USER, NOW, fixture.options);
  assert.equal(result.status, "already_attempted");
  assert.equal(fixture.sends.length, 0);
});

test("outside 18:30–19:00 local window costs no history read", async () => {
  let reads = 0;
  const fixture = deps({
    fetchHistory: async () => { reads += 1; return calendarHistory(); },
  });
  const result = await relationsUserOnce(USER, NOW - 3600000, fixture.options);
  assert.equal(result.reason, "outside-window");
  assert.equal(reads, 0);
});
