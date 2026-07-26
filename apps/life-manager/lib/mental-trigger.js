"use strict";
// 12a MEN-a — schedule-aware affirmation trigger engine (§9.11 MENTAL).
// Decides the "effective moment" from schedule + location + the immediately
// preceding event. Fixed clock times are forbidden by construction: with no
// schedule context there is never a send. Hard cap 3/day, minimum spacing,
// and suppression while mid-event or moving. Three trigger shapes only:
// pre_event (before an important event), between_events (the trough after an
// intense block), pre_sleep (approaching the user's own bedtime goal).

const TRIGGERS = Object.freeze(["pre_event", "between_events", "pre_sleep"]);
const LOCATION_STATES = Object.freeze(["home", "venue", "moving", "unknown"]);

const DAILY_CAP = 3;
const MIN_GAP_MS = 2 * 60 * 60 * 1000;
const PRE_EVENT_MIN_MS = 10 * 60 * 1000;
const PRE_EVENT_MAX_MS = 45 * 60 * 1000;
const TROUGH_AFTER_MS = 30 * 60 * 1000;
const TROUGH_CLEARANCE_MS = 60 * 60 * 1000;
const PRE_SLEEP_MIN_MS = 15 * 60 * 1000;
const PRE_SLEEP_MAX_MS = 60 * 60 * 1000;

const INPUT_KEYS = Object.freeze([
  "nowMs", "sentTodayCount", "lastSentMs", "events", "sleepTargetMs", "location",
]);
const EVENT_KEYS = Object.freeze(["startMs", "endMs", "important", "intense"]);

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Number.isInteger(input.sentTodayCount) || input.sentTodayCount < 0) throw new Error("sentTodayCount must be a non-negative integer");
  if (input.lastSentMs !== null && !Number.isFinite(input.lastSentMs)) throw new Error("lastSentMs must be null or a finite number");
  if (!Array.isArray(input.events)) throw new Error("events must be an array");
  for (const event of input.events) {
    if (!event || typeof event !== "object") throw new Error("event must be an object");
    for (const key of Object.keys(event)) {
      if (!EVENT_KEYS.includes(key)) throw new Error(`unknown key: event.${key}`);
    }
    if (!Number.isFinite(event.startMs) || !Number.isFinite(event.endMs) || event.endMs <= event.startMs) {
      throw new Error("event must have finite startMs < endMs");
    }
    if (typeof event.important !== "boolean" || typeof event.intense !== "boolean") {
      throw new Error("event.important and event.intense must be booleans");
    }
  }
  if (input.sleepTargetMs !== null && !Number.isFinite(input.sleepTargetMs)) throw new Error("sleepTargetMs must be null or a finite number");
  if (!input.location || !LOCATION_STATES.includes(input.location.state)) {
    throw new Error(`location.state must be one of ${LOCATION_STATES.join("|")}`);
  }
  return input;
}

function evaluateMentalTrigger(input) {
  validateInput(input);
  const { nowMs, events } = input;

  if (input.sentTodayCount >= DAILY_CAP) return { decision: "suppress", reason: "daily-cap-reached" };
  if (input.lastSentMs !== null && nowMs - input.lastSentMs < MIN_GAP_MS) {
    return { decision: "suppress", reason: "too-soon-after-last" };
  }
  if (events.some((e) => nowMs >= e.startMs && nowMs < e.endMs)) {
    return { decision: "suppress", reason: "mid-event" };
  }
  if (input.location.state === "moving") return { decision: "suppress", reason: "user-moving" };

  const upcoming = events.filter((e) => e.startMs > nowMs).sort((a, b) => a.startMs - b.startMs);
  const next = upcoming[0];

  if (next && next.important) {
    const lead = next.startMs - nowMs;
    if (lead >= PRE_EVENT_MIN_MS && lead <= PRE_EVENT_MAX_MS) {
      return { decision: "send", trigger: "pre_event", reason: "effective-moment-before-important-event" };
    }
  }

  const previous = events.filter((e) => e.endMs <= nowMs).sort((a, b) => b.endMs - a.endMs)[0];
  if (previous && previous.intense && nowMs - previous.endMs <= TROUGH_AFTER_MS &&
      (!next || next.startMs - nowMs >= TROUGH_CLEARANCE_MS)) {
    return { decision: "send", trigger: "between_events", reason: "trough-after-intense-block" };
  }

  if (input.sleepTargetMs !== null && upcoming.length === 0) {
    const untilSleep = input.sleepTargetMs - nowMs;
    if (untilSleep >= PRE_SLEEP_MIN_MS && untilSleep <= PRE_SLEEP_MAX_MS) {
      return { decision: "send", trigger: "pre_sleep", reason: "approaching-bedtime-goal" };
    }
  }

  return { decision: "suppress", reason: "no-effective-moment" };
}

// MIN_GAP_MS is exported because H4 (precepts) shares this organ's budget rather than opening a
// second one: the precepts question IS a MENTAL send for cap purposes, so it must read the SAME cap
// and the SAME spacing from the same constant. A copied `2 * 60 * 60 * 1000` in another file is a
// second budget wearing the first one's name.
module.exports = { TRIGGERS, LOCATION_STATES, DAILY_CAP, MIN_GAP_MS, validateInput, evaluateMentalTrigger };
