"use strict";
// H4 ORG-precepts — the observation trigger (spec §10 NEXT HORIZON row H4 ①/⑤).
//
// The MENTAL organ's shape, applied to the last quiet half hour of the day: a PURE decision function
// with no clock, no I/O and no env, so every reason to stay silent is testable and none of them can
// be quietly skipped. As with H2, the silences are the product.
//
// This question is the most intrusive thing the product asks, so it is bounded harder than any other
// organ's:
//   ONCE A WEEK. Seven days from the last ask, read from the ledger rather than from memory. A daily
//     version of this question is a daily invitation to feel bad, which is the opposite of what
//     noticing is for.
//   INSIDE MENTAL'S BUDGET (H4 ⑤ — 別枠にしない). The user sees one stream of unsolicited evening
//     messages; two organs each keeping politely to "3 a day" is six a day. So the 3/day cap and the
//     2h spacing here are MENTAL's own constants, imported, not re-declared.
//   THE 30 MINUTES BEFORE THE USER'S OWN BEDTIME. Not a fixed hour — the same pre_sleep target
//     mental-runtime already resolves, in the user's own clock. Note the deliberate overlap with
//     MENTAL's pre_sleep window (15-60 min before the same target): if an affirmation went out
//     there, the 2h spacing above suppresses this question, so the two can never stack.
//
// H4 ③ binds this file too: nothing here classifies, scores or diagnoses. It decides WHEN to ask.
// What the answer means is the ledger's business, and what it says about the person is nobody's.

const { LOCATION_STATES, DAILY_CAP, MIN_GAP_MS } = require("./mental-trigger.js");
const { PRECEPTS_STRINGS } = require("./i18n.js");

// The 五戒 in ordinary Japanese. The stored value is an ASCII token so the ledger never has to hold
// a sentence about a person, and the label the user actually read is derived from the copy below.
const PRECEPTS_ANSWERS = Object.freeze(["lie", "harsh", "time", "impulse", "calm"]);
// The one answer that is not a thing that snagged. It is still recorded — a calm day is an
// observation, and dropping it would make the mirror's counts a highlight reel of bad nights.
const PRECEPTS_CALM = "calm";

const PRECEPTS_MIN_GAP_MS = 7 * 86400000; // at most once per week (H4 ①)
const PRECEPTS_WINDOW_MS = 30 * 60000;    // the 30 minutes before the bedtime target

const INPUT_KEYS = Object.freeze([
  "nowMs", "sleepTargetMs", "sentTodayCount", "lastMentalSentMs", "lastAskMs", "events", "location",
]);

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (input.sleepTargetMs !== null && !Number.isFinite(input.sleepTargetMs)) {
    throw new Error("sleepTargetMs must be null or a finite number");
  }
  if (!Number.isInteger(input.sentTodayCount) || input.sentTodayCount < 0) {
    throw new Error("sentTodayCount must be a non-negative integer");
  }
  if (input.lastMentalSentMs !== null && !Number.isFinite(input.lastMentalSentMs)) {
    throw new Error("lastMentalSentMs must be null or a finite number");
  }
  if (input.lastAskMs !== null && !Number.isFinite(input.lastAskMs)) {
    throw new Error("lastAskMs must be null or a finite number");
  }
  if (!Array.isArray(input.events)) throw new Error("events must be an array");
  for (const event of input.events) {
    if (!event || typeof event !== "object") throw new Error("event must be an object");
    if (!Number.isFinite(event.startMs) || !Number.isFinite(event.endMs) || event.endMs <= event.startMs) {
      throw new Error("event must have finite startMs < endMs");
    }
  }
  if (!input.location || !LOCATION_STATES.includes(input.location.state)) {
    throw new Error(`location.state must be one of ${LOCATION_STATES.join("|")}`);
  }
  return input;
}

// Cheapest and most binding refusals first, so the reported reason is the one that would still hold
// if every other condition changed: a spent MENTAL budget is spent whatever the clock says.
function evaluatePreceptsAsk(input) {
  validateInput(input);
  const { nowMs, events } = input;

  if (input.sentTodayCount >= DAILY_CAP) {
    return { decision: "suppress", reason: "mental-daily-cap-reached" };
  }
  if (input.lastMentalSentMs !== null && nowMs - input.lastMentalSentMs < MIN_GAP_MS) {
    return { decision: "suppress", reason: "too-soon-after-mental-send" };
  }
  if (input.lastAskMs !== null && nowMs - input.lastAskMs < PRECEPTS_MIN_GAP_MS) {
    return { decision: "suppress", reason: "weekly-spacing" };
  }
  // Half-open, like mental-trigger: an event ending exactly now is over, one starting exactly now
  // has begun. Otherwise a back-to-back calendar would leave a one-tick hole to interrupt through.
  if (events.some((e) => nowMs >= e.startMs && nowMs < e.endMs)) {
    return { decision: "suppress", reason: "mid-event" };
  }
  if (input.location.state === "moving") return { decision: "suppress", reason: "user-moving" };

  // No bedtime target means no window, and an invented bedtime would ask this question at an hour
  // the user has not agreed to be asked anything.
  if (input.sleepTargetMs === null) return { decision: "suppress", reason: "no-sleep-target" };
  const untilSleep = input.sleepTargetMs - nowMs;
  if (untilSleep < 0 || untilSleep > PRECEPTS_WINDOW_MS) {
    return { decision: "suppress", reason: "outside-bedtime-window" };
  }
  return { decision: "ask", reason: "bedtime-window" };
}

// §9.5: a closed question. Five taps, no free-text path, and the labels are quoted from the copy so
// the keyboard cannot drift from the sentence above it.
//
// Each button CARRIES the day it was asked about, for the reason dietQuestionMessage documents: a
// Telegram keyboard has no expiry of its own, the question sits in the chat forever, and a tap that
// lands next week would otherwise be filed as next week's night — a fabricated data point in the one
// ledger whose whole value is that every row is something the user actually said. Callback data is
// capped at 64 bytes by Telegram; the longest of these is 34.
function preceptsQuestionMessage(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(day || ""))) {
    throw new Error("preceptsQuestionMessage needs the local day (YYYY-MM-DD) the question belongs to");
  }
  const copy = PRECEPTS_STRINGS.ja.nightQuestion;
  const tap = (answer) => `precepts:answer:${answer}:${day}`;
  return {
    text: copy.text,
    extra: { reply_markup: { inline_keyboard: [[
      { text: copy.lieButton, callback_data: tap("lie") },
      { text: copy.harshButton, callback_data: tap("harsh") },
    ], [
      { text: copy.timeButton, callback_data: tap("time") },
      { text: copy.impulseButton, callback_data: tap("impulse") },
    ], [
      { text: copy.calmButton, callback_data: tap("calm") },
    ]] } },
  };
}

// answer value → the label the user actually tapped, for CB-1's visible edit, the already-recorded
// reply and the weekly mirror's counts. Derived from the copy, never restated.
const PRECEPTS_ANSWER_LABELS = Object.freeze({
  lie: PRECEPTS_STRINGS.ja.nightQuestion.lieButton,
  harsh: PRECEPTS_STRINGS.ja.nightQuestion.harshButton,
  time: PRECEPTS_STRINGS.ja.nightQuestion.timeButton,
  impulse: PRECEPTS_STRINGS.ja.nightQuestion.impulseButton,
  calm: PRECEPTS_STRINGS.ja.nightQuestion.calmButton,
});

module.exports = {
  PRECEPTS_ANSWERS,
  PRECEPTS_ANSWER_LABELS,
  PRECEPTS_CALM,
  PRECEPTS_MIN_GAP_MS,
  PRECEPTS_WINDOW_MS,
  MENTAL_DAILY_CAP: DAILY_CAP,
  MENTAL_MIN_GAP_MS: MIN_GAP_MS,
  validateInput,
  evaluatePreceptsAsk,
  preceptsQuestionMessage,
};
