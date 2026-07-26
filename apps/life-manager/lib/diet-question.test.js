"use strict";
// H2 ORG-diet — the observation trigger. The whole point of the organ is that it asks RARELY and only
// in the moment the answer is cheap to give: the middle of the user's own lunch gap. These tests pin
// every reason it must stay silent, because a diet question that fires at the wrong hour, during a
// meeting, or four days running is the exact thing that gets the product uninstalled.
// Run: node --test lib/diet-question.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  evaluateDietQuestion,
  dietQuestionMessage,
  DIET_ANSWERS,
  DIET_WEEKLY_CAP,
  DIET_MIN_GAP_MS,
  WINDOW_START_MIN,
  WINDOW_END_MIN,
} = require("./diet-question.js");
const { DIET_STRINGS } = require("./i18n.js");

const JST = 9;
// 2026-07-27 12:00 JST = 03:00Z — dead centre of the window.
const NOON_JST = Date.parse("2026-07-27T03:00:00Z");

function at(localHHMM, tzOffsetH = JST) {
  const [h, m] = localHHMM.split(":").map(Number);
  return Date.parse("2026-07-27T00:00:00Z") + (h - tzOffsetH) * 3600000 + m * 60000;
}

function input(overrides = {}) {
  return {
    nowMs: NOON_JST,
    tzOffsetH: JST,
    events: [],
    askedThisWeek: 0,
    lastAskMs: null,
    location: { state: "unknown" },
    ...overrides,
  };
}

// ── the window, in the USER's clock ───────────────────────────────────────────────────────────────

test("the lunch window is 11:30-13:30 in the user's local time, inclusive at both ends", () => {
  assert.equal(WINDOW_START_MIN, 11 * 60 + 30);
  assert.equal(WINDOW_END_MIN, 13 * 60 + 30);
  assert.equal(evaluateDietQuestion(input({ nowMs: at("11:30") })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({ nowMs: at("13:30") })).decision, "ask");
});

test("one minute before 11:30 and one minute after 13:30 are silent", () => {
  const before = evaluateDietQuestion(input({ nowMs: at("11:29") }));
  assert.equal(before.decision, "suppress");
  assert.equal(before.reason, "outside-lunch-window");
  assert.equal(evaluateDietQuestion(input({ nowMs: at("13:31") })).reason, "outside-lunch-window");
});

test("the window follows the timezone, not UTC — 03:00Z is lunch in JST and midnight in UTC", () => {
  assert.equal(evaluateDietQuestion(input({ nowMs: NOON_JST, tzOffsetH: 9 })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({ nowMs: NOON_JST, tzOffsetH: 0 })).decision, "suppress");
});

test("a negative offset works too: 12:00 in UTC-5 is 17:00Z", () => {
  assert.equal(evaluateDietQuestion(input({ nowMs: at("12:00", -5), tzOffsetH: -5 })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({ nowMs: at("09:00", -5), tzOffsetH: -5 })).decision, "suppress");
});

test("the local-day rollover does not smear the window across midnight", () => {
  // 12:00 JST on the NEXT day must still be inside the window, not shifted by the wrap.
  assert.equal(evaluateDietQuestion(input({ nowMs: NOON_JST + 86400000 })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({ nowMs: NOON_JST + 43200000 })).decision, "suppress"); // 24:00 JST
});

// ── the caps ──────────────────────────────────────────────────────────────────────────────────────

test("three asks in a week is the cap; the fourth is refused", () => {
  assert.equal(DIET_WEEKLY_CAP, 3);
  assert.equal(evaluateDietQuestion(input({ askedThisWeek: 2 })).decision, "ask");
  const capped = evaluateDietQuestion(input({ askedThisWeek: 3 }));
  assert.equal(capped.decision, "suppress");
  assert.equal(capped.reason, "weekly-cap-reached");
});

test("48h must pass between asks — 47h59m is still too soon", () => {
  assert.equal(DIET_MIN_GAP_MS, 48 * 3600000);
  const tooSoon = evaluateDietQuestion(input({ lastAskMs: NOON_JST - (48 * 3600000 - 60000) }));
  assert.equal(tooSoon.decision, "suppress");
  assert.equal(tooSoon.reason, "too-soon-after-last");
  assert.equal(evaluateDietQuestion(input({ lastAskMs: NOON_JST - 48 * 3600000 })).decision, "ask");
});

test("the cap is checked before the spacing, so a capped week reports the cap", () => {
  const both = evaluateDietQuestion(input({ askedThisWeek: 3, lastAskMs: NOON_JST - 1000 }));
  assert.equal(both.reason, "weekly-cap-reached");
});

// ── MENTAL's suppression, inherited verbatim (spec H2 ⑤) ──────────────────────────────────────────

test("an event in progress silences the question", () => {
  const midEvent = evaluateDietQuestion(input({
    events: [{ startMs: NOON_JST - 600000, endMs: NOON_JST + 600000 }],
  }));
  assert.equal(midEvent.decision, "suppress");
  assert.equal(midEvent.reason, "mid-event");
});

test("an event that ended, or has not started, does not silence anything", () => {
  assert.equal(evaluateDietQuestion(input({
    events: [{ startMs: NOON_JST - 7200000, endMs: NOON_JST - 3600000 },
      { startMs: NOON_JST + 3600000, endMs: NOON_JST + 7200000 }],
  })).decision, "ask");
});

test("the boundary is half-open: an event ending exactly now is over", () => {
  assert.equal(evaluateDietQuestion(input({
    events: [{ startMs: NOON_JST - 3600000, endMs: NOON_JST }],
  })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({
    events: [{ startMs: NOON_JST, endMs: NOON_JST + 3600000 }],
  })).decision, "suppress");
});

test("a moving user is silenced; unknown location never silences", () => {
  const moving = evaluateDietQuestion(input({ location: { state: "moving" } }));
  assert.equal(moving.decision, "suppress");
  assert.equal(moving.reason, "user-moving");
  assert.equal(evaluateDietQuestion(input({ location: { state: "unknown" } })).decision, "ask");
  assert.equal(evaluateDietQuestion(input({ location: { state: "venue" } })).decision, "ask");
});

// ── input discipline: a malformed input is a bug, never a silent "ask" ─────────────────────────────

test("bad inputs throw rather than defaulting into a send", () => {
  assert.throws(() => evaluateDietQuestion(null), /input must be an object/);
  assert.throws(() => evaluateDietQuestion(input({ nowMs: NaN })), /nowMs/);
  assert.throws(() => evaluateDietQuestion(input({ tzOffsetH: "9" })), /tzOffsetH/);
  assert.throws(() => evaluateDietQuestion(input({ askedThisWeek: -1 })), /askedThisWeek/);
  assert.throws(() => evaluateDietQuestion(input({ lastAskMs: "yesterday" })), /lastAskMs/);
  assert.throws(() => evaluateDietQuestion(input({ events: "none" })), /events must be an array/);
  assert.throws(() => evaluateDietQuestion(input({ location: { state: "teleporting" } })), /location\.state/);
  assert.throws(() => evaluateDietQuestion({ ...input(), surprise: 1 }), /unknown key/);
});

// ── the closed question itself (spec H2 ①, §9.5: closed, tap-only, no free text) ───────────────────

test("the question is exactly four taps and no free-text answer", () => {
  const message = dietQuestionMessage("2026-07-27");
  assert.equal(message.text, DIET_STRINGS.ja.lunchQuestion.text);
  const buttons = message.extra.reply_markup.inline_keyboard.flat();
  assert.equal(buttons.length, 4);
  // The ask day travels IN the button: a tap that arrives tomorrow must be filed against the lunch
  // it was actually about, or refused — never silently recorded as today's.
  assert.deepEqual(buttons.map((b) => b.callback_data), [
    "diet:answer:teishoku:2026-07-27", "diet:answer:men:2026-07-27",
    "diet:answer:fast:2026-07-27", "diet:answer:skip:2026-07-27",
  ]);
  assert.deepEqual(DIET_ANSWERS, ["teishoku", "men", "fast", "skip"]);
});

test("the question refuses to be built without the day it belongs to", () => {
  assert.throws(() => dietQuestionMessage(), /day/);
  assert.throws(() => dietQuestionMessage("27 July"), /day/);
});

test("the button labels come from the Dais-editable copy, never restated in code", () => {
  const copy = DIET_STRINGS.ja.lunchQuestion;
  assert.deepEqual(dietQuestionMessage("2026-07-27").extra.reply_markup.inline_keyboard.flat().map((b) => b.text), [
    copy.teishokuButton, copy.menButton, copy.fastButton, copy.skipButton,
  ]);
  // Every label must actually appear in the sentence the user reads — copy and keyboard cannot drift.
  for (const label of [copy.teishokuButton, copy.menButton, copy.fastButton, copy.skipButton]) {
    assert.ok(copy.text.includes(label), `question text must name ${label}`);
  }
});

test("the copy diagnoses nothing (spec H2 ⑥: record the choice, never judge it)", () => {
  const copy = DIET_STRINGS.ja.lunchQuestion;
  assert.doesNotMatch(copy.text, /健康|カロリー|太|痩|栄養|ダイエット/);
  assert.ok(copy.text.startsWith("今日のお昼は?"), copy.text);
});
