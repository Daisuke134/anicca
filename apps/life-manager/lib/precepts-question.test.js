"use strict";
// H4 ORG-precepts — the pure trigger. Every reason to stay silent is a test, because the silences are
// the product: this is the most intrusive question the product asks, and the only thing standing
// between it and a nightly interrogation is arithmetic that nobody can quietly delete.
// Run: node --test lib/precepts-question.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  PRECEPTS_ANSWERS, PRECEPTS_ANSWER_LABELS, PRECEPTS_MIN_GAP_MS, PRECEPTS_WINDOW_MS,
  MENTAL_DAILY_CAP, MENTAL_MIN_GAP_MS, evaluatePreceptsAsk, preceptsQuestionMessage,
} = require("./precepts-question.js");
const { DAILY_CAP, MIN_GAP_MS } = require("./mental-trigger.js");
const { PRECEPTS_STRINGS } = require("./i18n.js");

const NOW = Date.parse("2026-07-27T14:10:00Z"); // 23:10 JST
const SLEEP = Date.parse("2026-07-27T14:30:00Z"); // 23:30 JST — 20 minutes out

function input(overrides = {}) {
  return {
    nowMs: NOW,
    sleepTargetMs: SLEEP,
    sentTodayCount: 0,
    lastMentalSentMs: null,
    lastAskMs: null,
    events: [],
    location: { state: "unknown" },
    ...overrides,
  };
}

test("in the 30 minutes before the user's own bedtime, with a clean history, it asks", () => {
  assert.deepEqual(evaluatePreceptsAsk(input()), { decision: "ask", reason: "bedtime-window" });
});

// ── the MENTAL budget is shared, not duplicated (H4 ⑤) ────────────────────────────────────────────

test("the cap and the spacing are MENTAL's own constants, imported rather than re-declared", () => {
  assert.equal(MENTAL_DAILY_CAP, DAILY_CAP);
  assert.equal(MENTAL_MIN_GAP_MS, MIN_GAP_MS);
  assert.equal(MENTAL_DAILY_CAP, 3);
  assert.equal(MENTAL_MIN_GAP_MS, 2 * 60 * 60 * 1000);
});

test("a day that already spent MENTAL's three sends gets no precepts question", () => {
  const verdict = evaluatePreceptsAsk(input({ sentTodayCount: 3 }));
  assert.deepEqual(verdict, { decision: "suppress", reason: "mental-daily-cap-reached" });
  // The cap is a cap, not a target: four is still refused, and the reason does not drift.
  assert.equal(evaluatePreceptsAsk(input({ sentTodayCount: 9 })).reason, "mental-daily-cap-reached");
});

test("an affirmation sent within the last 2 hours suppresses the question", () => {
  const justUnder = evaluatePreceptsAsk(input({ lastMentalSentMs: NOW - MIN_GAP_MS + 60000 }));
  assert.deepEqual(justUnder, { decision: "suppress", reason: "too-soon-after-mental-send" });
  // MENTAL's own pre_sleep window (15-60 min before the same target) overlaps this one on purpose;
  // the spacing is what makes them unable to stack.
  const clear = evaluatePreceptsAsk(input({ lastMentalSentMs: NOW - MIN_GAP_MS }));
  assert.equal(clear.decision, "ask");
});

test("the cap outranks everything else — it is reported even when the clock is also wrong", () => {
  const verdict = evaluatePreceptsAsk(input({
    sentTodayCount: 3, lastAskMs: NOW - 1000, sleepTargetMs: NOW + 10 * 3600000,
    location: { state: "moving" },
  }));
  assert.equal(verdict.reason, "mental-daily-cap-reached",
    "the reported reason must be the one that would still hold if everything else changed");
});

// ── once a week ───────────────────────────────────────────────────────────────────────────────────

test("seven days of spacing, to the millisecond, read from the caller's ledger state", () => {
  assert.equal(PRECEPTS_MIN_GAP_MS, 7 * 86400000);
  assert.equal(evaluatePreceptsAsk(input({ lastAskMs: NOW - PRECEPTS_MIN_GAP_MS + 1 })).reason, "weekly-spacing");
  assert.equal(evaluatePreceptsAsk(input({ lastAskMs: NOW - PRECEPTS_MIN_GAP_MS })).decision, "ask");
  assert.equal(evaluatePreceptsAsk(input({ lastAskMs: NOW - 86400000 })).reason, "weekly-spacing",
    "yesterday's question makes tonight's a daily interrogation");
});

// ── the window ────────────────────────────────────────────────────────────────────────────────────

test("the window is the 30 minutes BEFORE the target, never after and never earlier", () => {
  assert.equal(PRECEPTS_WINDOW_MS, 30 * 60000);
  assert.equal(evaluatePreceptsAsk(input({ nowMs: SLEEP - PRECEPTS_WINDOW_MS })).decision, "ask", "the far edge");
  assert.equal(evaluatePreceptsAsk(input({ nowMs: SLEEP })).decision, "ask", "the near edge");
  assert.equal(evaluatePreceptsAsk(input({ nowMs: SLEEP - PRECEPTS_WINDOW_MS - 1 })).reason, "outside-bedtime-window");
  assert.equal(evaluatePreceptsAsk(input({ nowMs: SLEEP + 1 })).reason, "outside-bedtime-window",
    "after bedtime the question is an alarm clock, not a reflection");
});

test("no bedtime target means no window — an invented one would ask at an unagreed hour", () => {
  assert.deepEqual(evaluatePreceptsAsk(input({ sleepTargetMs: null })),
    { decision: "suppress", reason: "no-sleep-target" });
});

// ── the ordinary suppressions ─────────────────────────────────────────────────────────────────────

test("mid-event and moving suppress, with half-open event bounds", () => {
  const midEvent = [{ startMs: NOW - 600000, endMs: NOW + 600000 }];
  assert.equal(evaluatePreceptsAsk(input({ events: midEvent })).reason, "mid-event");
  // An event ending exactly now is over; one starting exactly now has begun.
  assert.equal(evaluatePreceptsAsk(input({ events: [{ startMs: NOW - 600000, endMs: NOW }] })).decision, "ask");
  assert.equal(evaluatePreceptsAsk(input({ events: [{ startMs: NOW, endMs: NOW + 600000 }] })).reason, "mid-event");
  assert.equal(evaluatePreceptsAsk(input({ location: { state: "moving" } })).reason, "user-moving");
  assert.equal(evaluatePreceptsAsk(input({ location: { state: "home" } })).decision, "ask");
});

// ── the schema is closed, and the function is pure ────────────────────────────────────────────────

test("unknown keys and malformed values are refused rather than coerced", () => {
  assert.throws(() => evaluatePreceptsAsk({ ...input(), surprise: 1 }), /unknown key/);
  assert.throws(() => evaluatePreceptsAsk(input({ nowMs: "now" })), /nowMs/);
  assert.throws(() => evaluatePreceptsAsk(input({ sentTodayCount: -1 })), /sentTodayCount/);
  assert.throws(() => evaluatePreceptsAsk(input({ sentTodayCount: 1.5 })), /sentTodayCount/);
  assert.throws(() => evaluatePreceptsAsk(input({ lastAskMs: "yesterday" })), /lastAskMs/);
  assert.throws(() => evaluatePreceptsAsk(input({ location: { state: "somewhere" } })), /location.state/);
  assert.throws(() => evaluatePreceptsAsk(input({ events: [{ startMs: 1, endMs: 1 }] })), /startMs < endMs/);
});

test("identical input yields identical output — no clock, no env, no I/O", () => {
  const a = evaluatePreceptsAsk(input());
  const b = evaluatePreceptsAsk(input());
  assert.deepEqual(a, b);
});

// ── the message ───────────────────────────────────────────────────────────────────────────────────

test("five taps, quoted from the copy, each carrying the night it belongs to", () => {
  const message = preceptsQuestionMessage("2026-07-27");
  const copy = PRECEPTS_STRINGS.ja.nightQuestion;
  assert.equal(message.text, copy.text);
  const buttons = message.extra.reply_markup.inline_keyboard.flat();
  assert.equal(buttons.length, 5);
  assert.deepEqual(buttons.map((b) => b.text), [
    copy.lieButton, copy.harshButton, copy.timeButton, copy.impulseButton, copy.calmButton,
  ]);
  assert.deepEqual(buttons.map((b) => b.callback_data), [
    "precepts:answer:lie:2026-07-27", "precepts:answer:harsh:2026-07-27",
    "precepts:answer:time:2026-07-27", "precepts:answer:impulse:2026-07-27",
    "precepts:answer:calm:2026-07-27",
  ]);
  // Telegram's hard limit. A callback that silently truncates is a tap that files the wrong night.
  for (const button of buttons) {
    assert.ok(Buffer.byteLength(button.callback_data) <= 64, button.callback_data);
  }
});

test("the labels the mirror and the CB-1 edit use come from the copy, never restated", () => {
  const copy = PRECEPTS_STRINGS.ja.nightQuestion;
  assert.deepEqual(PRECEPTS_ANSWERS, ["lie", "harsh", "time", "impulse", "calm"]);
  assert.deepEqual(PRECEPTS_ANSWER_LABELS, {
    lie: copy.lieButton, harsh: copy.harshButton, time: copy.timeButton,
    impulse: copy.impulseButton, calm: copy.calmButton,
  });
  // The sentence the user reads and the buttons they tap cannot drift apart.
  for (const label of Object.values(PRECEPTS_ANSWER_LABELS)) assert.ok(copy.text.includes(label), label);
});

test("a message without a day is refused — a dayless keyboard files taps against the wrong night", () => {
  for (const bad of [undefined, null, "", "2026-7-27", "tonight"]) {
    assert.throws(() => preceptsQuestionMessage(bad), /local day/);
  }
});

// ── the tone rules the copy has to carry (§9.11 + H4 ①③) ──────────────────────────────────────────

test("no religious vocabulary reaches the user, in any string this organ can send", () => {
  const strings = JSON.stringify(PRECEPTS_STRINGS);
  for (const word of ["戒", "罪", "業", "懺悔", "煩悩", "悟", "修行", "善", "悪", "仏", "徳"]) {
    assert.ok(!strings.includes(word), `「${word}」 must never appear in precepts copy`);
  }
});

test("no scoring and no advice, either — the templates are where those are prevented", () => {
  const strings = JSON.stringify(PRECEPTS_STRINGS);
  for (const word of ["点数", "評価", "スコア", "改善", "悪化", "合計", "平均", "ランク"]) {
    assert.ok(!strings.includes(word), `「${word}」 turns a mirror into a report card`);
  }
  for (const word of ["しましょう", "ましょう", "べき", "おすすめ", "控え", "頑張"]) {
    assert.ok(!strings.includes(word), `「${word}」 is advice, and H4 ③ forbids it`);
  }
});

test("§9.11 voice: one leading emoji at most, and the question is closed", () => {
  const copy = PRECEPTS_STRINGS.ja.nightQuestion;
  const emoji = /\p{Extended_Pictographic}/gu;
  assert.equal((copy.text.match(emoji) || []).length, 0, "the question needs no decoration");
  for (const template of Object.values(PRECEPTS_STRINGS.ja.weeklyMirror)) {
    const found = String(template).match(emoji) || [];
    assert.ok(found.length <= 1, `at most one emoji: ${template}`);
    if (found.length === 1) assert.ok(String(template).startsWith(found[0]), "and it leads the message");
  }
  // The mirror asks for nothing (§9.11 ④) — no question mark anywhere in it.
  for (const [key, template] of Object.entries(PRECEPTS_STRINGS.ja.weeklyMirror)) {
    assert.ok(!/[?？]/.test(String(template)), `the mirror must not ask a question: ${key}`);
  }
});
