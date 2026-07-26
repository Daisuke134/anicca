"use strict";
// H2 ORG-diet — the observation trigger (spec §10 NEXT HORIZON row H2 ①/⑤).
//
// The MENTAL organ's shape, applied to lunch: a PURE decision function with no clock, no I/O and no
// env, so every reason to stay silent is testable and none of them can be quietly skipped. The
// silences are the product. An unsolicited question about food is only tolerable if it arrives in
// the gap where the answer costs one tap — the middle of the user's own lunch hour, at most three
// times a week, never twice in 48 hours, never while they are in a meeting or on the move.
//
// The window lives in the USER's clock, not UTC: 12:00 in Tokyo and 12:00 in Berlin are different
// instants and the same moment in a person's day, so tzOffsetH is a required input rather than a
// default that would silently ask a European user at 3am.
//
// H2 ⑥ is a constraint on this file too: nothing here classifies, scores or diagnoses. It decides
// WHEN to ask. What the answer means is the ledger's business, and what it says about the person is
// nobody's business.

const { LOCATION_STATES } = require("./mental-trigger.js");
const { DIET_STRINGS } = require("./i18n.js");

const DIET_ANSWERS = Object.freeze(["teishoku", "men", "fast", "skip"]);
const DIET_WEEKLY_CAP = 3;
const DIET_MIN_GAP_MS = 48 * 60 * 60 * 1000;
const WINDOW_START_MIN = 11 * 60 + 30; // 11:30 local
const WINDOW_END_MIN = 13 * 60 + 30; // 13:30 local, inclusive

const INPUT_KEYS = Object.freeze([
  "nowMs", "tzOffsetH", "events", "askedThisWeek", "lastAskMs", "location",
]);

// Minutes since local midnight. The modulo is taken AFTER the offset so a negative offset (the
// Americas) wraps into the previous local day instead of going negative.
function localMinuteOfDay(nowMs, tzOffsetH) {
  const localMs = nowMs + tzOffsetH * 3600000;
  const dayMs = ((localMs % 86400000) + 86400000) % 86400000;
  return Math.floor(dayMs / 60000);
}

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Number.isFinite(input.tzOffsetH)) throw new Error("tzOffsetH must be a finite number");
  if (!Array.isArray(input.events)) throw new Error("events must be an array");
  for (const event of input.events) {
    if (!event || typeof event !== "object") throw new Error("event must be an object");
    if (!Number.isFinite(event.startMs) || !Number.isFinite(event.endMs) || event.endMs <= event.startMs) {
      throw new Error("event must have finite startMs < endMs");
    }
  }
  if (!Number.isInteger(input.askedThisWeek) || input.askedThisWeek < 0) {
    throw new Error("askedThisWeek must be a non-negative integer");
  }
  if (input.lastAskMs !== null && !Number.isFinite(input.lastAskMs)) {
    throw new Error("lastAskMs must be null or a finite number");
  }
  if (!input.location || !LOCATION_STATES.includes(input.location.state)) {
    throw new Error(`location.state must be one of ${LOCATION_STATES.join("|")}`);
  }
  return input;
}

// Cheapest and most binding refusals first, so the reported reason is the one that would still hold
// if every other condition changed: a capped week is a capped week whatever the clock says.
function evaluateDietQuestion(input) {
  validateInput(input);
  const { nowMs, tzOffsetH, events } = input;

  if (input.askedThisWeek >= DIET_WEEKLY_CAP) return { decision: "suppress", reason: "weekly-cap-reached" };
  if (input.lastAskMs !== null && nowMs - input.lastAskMs < DIET_MIN_GAP_MS) {
    return { decision: "suppress", reason: "too-soon-after-last" };
  }
  // Half-open, like mental-trigger: an event ending exactly now is over, one starting exactly now
  // has begun. Otherwise a back-to-back calendar would leave a one-tick hole to interrupt through.
  if (events.some((e) => nowMs >= e.startMs && nowMs < e.endMs)) {
    return { decision: "suppress", reason: "mid-event" };
  }
  if (input.location.state === "moving") return { decision: "suppress", reason: "user-moving" };

  const minute = localMinuteOfDay(nowMs, tzOffsetH);
  if (minute < WINDOW_START_MIN || minute > WINDOW_END_MIN) {
    return { decision: "suppress", reason: "outside-lunch-window" };
  }
  return { decision: "ask", reason: "lunch-gap" };
}

// §9.5: a closed question. Four taps, no free-text path, and the labels are quoted from the copy so
// the keyboard cannot drift from the sentence above it.
function dietQuestionMessage() {
  const copy = DIET_STRINGS.ja.lunchQuestion;
  return {
    text: copy.text,
    extra: { reply_markup: { inline_keyboard: [[
      { text: copy.teishokuButton, callback_data: "diet:answer:teishoku" },
      { text: copy.menButton, callback_data: "diet:answer:men" },
    ], [
      { text: copy.fastButton, callback_data: "diet:answer:fast" },
      { text: copy.skipButton, callback_data: "diet:answer:skip" },
    ]] } },
  };
}

// answer value → the label the user actually tapped, for CB-1's visible edit and the
// already-recorded reply. Derived from the copy, never restated.
const DIET_ANSWER_LABELS = Object.freeze({
  teishoku: DIET_STRINGS.ja.lunchQuestion.teishokuButton,
  men: DIET_STRINGS.ja.lunchQuestion.menButton,
  fast: DIET_STRINGS.ja.lunchQuestion.fastButton,
  skip: DIET_STRINGS.ja.lunchQuestion.skipButton,
});

module.exports = {
  DIET_ANSWERS,
  DIET_ANSWER_LABELS,
  DIET_WEEKLY_CAP,
  DIET_MIN_GAP_MS,
  WINDOW_START_MIN,
  WINDOW_END_MIN,
  localMinuteOfDay,
  validateInput,
  evaluateDietQuestion,
  dietQuestionMessage,
};
