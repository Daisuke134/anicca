"use strict";
// MEN-c: the MENTAL organ existed only inside an eval — nothing in production ever called it, so no
// message could reach anyone. These tests pin the runtime leg: read the real day, decide with the
// existing trigger rule, speak with the existing copy rule, and record what was actually delivered.
const assert = require("node:assert/strict");
const test = require("node:test");

const { mentalUserOnce } = require("./mental-runtime.js");
const { validateMentalMessage } = require("./mental-copy.js");

const NOW = Date.parse("2026-07-25T10:00:00+09:00");
const USER = { uid: "u1", telegram_chat_id: "7" };

function deps(overrides = {}) {
  const sent = [];
  const recorded = [];
  return {
    sent,
    recorded,
    base: {
      fetchUpcomingEvents: async () => [],
      getLocationState: async () => "home",
      readSendState: async () => ({ sentTodayCount: 0, lastSentMs: null }),
      recordSend: async (uid, trigger, messageId) => { recorded.push({ uid, trigger, messageId }); return true; },
      sendMessage: async (_token, _chat, text) => { sent.push(text); return { ok: true, result: { message_id: 900 + sent.length } }; },
      seeds: ["I am enough exactly as I am"],
      sleepTargetMs: null,
      telegramToken: "tg",
      ...overrides,
    },
  };
}

test("an important event in the effective window sends the pre-event line", async () => {
  const d = deps({
    fetchUpcomingEvents: async () => [
      { startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false },
    ],
  });
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.decision, "send");
  assert.equal(result.trigger, "pre_event");
  assert.equal(d.sent.length, 1);
  assert.equal(validateMentalMessage(d.sent[0]).ok, true);
  assert.equal(result.telegramMessageId, 901);
  assert.deepEqual(d.recorded, [{ uid: "u1", trigger: "pre_event", messageId: 901 }]);
});

test("nothing is sent or recorded when the moment is not effective", async () => {
  const d = deps();
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.decision, "suppress");
  assert.equal(d.sent.length, 0);
  assert.equal(d.recorded.length, 0);
});

test("the daily cap is honoured before anything is composed or sent", async () => {
  const d = deps({
    readSendState: async () => ({ sentTodayCount: 3, lastSentMs: null }),
    fetchUpcomingEvents: async () => [
      { startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false },
    ],
  });
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.decision, "suppress");
  assert.equal(result.reason, "daily-cap-reached");
  assert.equal(d.sent.length, 0);
});

test("a user in motion is left alone", async () => {
  const d = deps({
    getLocationState: async () => "moving",
    fetchUpcomingEvents: async () => [
      { startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false },
    ],
  });
  assert.equal((await mentalUserOnce(USER, NOW, d.base)).reason, "user-moving");
  assert.equal(d.sent.length, 0);
});

test("a user without a Telegram chat is never messaged", async () => {
  const d = deps({
    fetchUpcomingEvents: async () => [
      { startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false },
    ],
  });
  const result = await mentalUserOnce({ uid: "u2", telegram_chat_id: null }, NOW, d.base);

  assert.equal(result.decision, "suppress");
  assert.equal(result.reason, "unreachable");
  assert.equal(d.sent.length, 0);
});

test("a failed Telegram send is not recorded as delivered", async () => {
  const d = deps({
    fetchUpcomingEvents: async () => [
      { startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false },
    ],
    sendMessage: async () => ({ ok: false }),
  });
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.decision, "send");
  assert.equal(result.delivered, false);
  assert.equal(d.recorded.length, 0);
});

test("a calendar that cannot be read suppresses instead of guessing the day", async () => {
  const d = deps({ fetchUpcomingEvents: async () => { throw new Error("calendar down"); } });
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.decision, "suppress");
  assert.equal(result.reason, "calendar-unavailable");
  assert.equal(d.sent.length, 0);
});

test("the bedtime line goes out when the day is clear and sleep is approaching", async () => {
  const d = deps({ sleepTargetMs: NOW + 45 * 60000 });
  const result = await mentalUserOnce(USER, NOW, d.base);

  assert.equal(result.trigger, "pre_sleep");
  assert.equal(validateMentalMessage(d.sent[0]).ok, true);
});

test("every delivered line satisfies the 9.11 rule across all three triggers", async () => {
  const cases = [
    { name: "pre_event", opts: { fetchUpcomingEvents: async () => [{ startMs: NOW + 20 * 60000, endMs: NOW + 80 * 60000, important: true, intense: false }] } },
    { name: "between_events", opts: { fetchUpcomingEvents: async () => [{ startMs: NOW - 90 * 60000, endMs: NOW - 10 * 60000, important: false, intense: true }] } },
    { name: "pre_sleep", opts: { sleepTargetMs: NOW + 45 * 60000 } },
  ];
  for (const testCase of cases) {
    const d = deps(testCase.opts);
    const result = await mentalUserOnce(USER, NOW, d.base);
    assert.equal(result.trigger, testCase.name, `expected ${testCase.name}, got ${result.trigger}`);
    assert.equal(validateMentalMessage(d.sent[0]).ok, true);
  }
});

// The bedtime line could never fire in production: nothing supplied a sleep target, so that branch of
// the trigger rule was unreachable. The target is a clock time in the user's day, resolved per tick.
test("a bedtime clock time resolves to today's instant", () => {
  const { resolveSleepTarget } = require("./mental-runtime.js");
  const now = Date.parse("2026-07-25T18:20:00+09:00");
  const target = resolveSleepTarget("23:30", now, 9);
  assert.equal(new Date(target).toISOString(), "2026-07-25T14:30:00.000Z");
  assert.ok(target > now);
});

test("a bedtime already past today rolls to the next day rather than firing in the past", () => {
  const { resolveSleepTarget } = require("./mental-runtime.js");
  const now = Date.parse("2026-07-26T00:40:00+09:00");
  const target = resolveSleepTarget("23:30", now, 9);
  assert.ok(target > now, "the target must always be ahead of now");
});

test("an unusable bedtime setting yields no target instead of a wrong one", () => {
  const { resolveSleepTarget } = require("./mental-runtime.js");
  const now = Date.parse("2026-07-25T18:20:00+09:00");
  for (const bad of ["", "25:00", "abc", null, "23:60"]) {
    assert.equal(resolveSleepTarget(bad, now, 9), null, `expected null for ${JSON.stringify(bad)}`);
  }
});
