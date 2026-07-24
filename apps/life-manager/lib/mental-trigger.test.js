"use strict";
// 12a MEN-a contract: closed input schema + the two invariants that must hold
// regardless of schedule shape — the 3/day cap always wins, and no schedule
// context can never produce a send (fixed clock times are impossible).
// The full decision matrix lives in eval/men-cases.jsonl.

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateInput, evaluateMentalTrigger, DAILY_CAP, TRIGGERS } = require("./mental-trigger.js");

const BASE = 1753344000000;
const H = 3600000;

function input(overrides = {}) {
  return {
    nowMs: BASE + 10 * H, sentTodayCount: 0, lastSentMs: null,
    events: [{ startMs: BASE + 10.5 * H, endMs: BASE + 11.5 * H, important: true, intense: false }],
    sleepTargetMs: null, location: { state: "home" },
    ...overrides,
  };
}

test("schema: closed keys and enums", () => {
  assert.deepEqual([...TRIGGERS], ["pre_event", "between_events", "pre_sleep"]);
  assert.doesNotThrow(() => validateInput(input()));
  assert.throws(() => validateInput({ ...input(), extra: 1 }), /unknown key/);
  assert.throws(() => validateInput(input({ sentTodayCount: -1 })), /sentTodayCount/);
  assert.throws(() => validateInput(input({ location: { state: "cafe" } })), /location/);
  assert.throws(() => validateInput(input({ events: [{ startMs: 2, endMs: 1, important: true, intense: false }] })), /startMs/);
  assert.throws(() => validateInput(input({ events: [{ startMs: 1, endMs: 2, important: true, intense: false, note: "x" }] })), /unknown key: event/);
});

test("cap: with 3 already sent today, every otherwise-perfect moment suppresses", () => {
  const perfect = input({ sentTodayCount: DAILY_CAP });
  assert.deepEqual(evaluateMentalTrigger(perfect), { decision: "suppress", reason: "daily-cap-reached" });
});

test("fixed-time prohibition: an empty schedule can never produce a send at any hour", () => {
  for (let hour = 0; hour < 24; hour++) {
    const out = evaluateMentalTrigger(input({ nowMs: BASE + hour * H, events: [], sleepTargetMs: null }));
    assert.equal(out.decision, "suppress", `hour ${hour} must suppress with no schedule context`);
  }
});

test("determinism: identical input yields identical output", () => {
  const a = evaluateMentalTrigger(input());
  const b = evaluateMentalTrigger(input());
  assert.deepEqual(a, b);
  assert.equal(a.decision, "send");
  assert.equal(a.trigger, "pre_event");
});
