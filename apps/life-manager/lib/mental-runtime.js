"use strict";
// MEN-c — the production leg of the MENTAL organ.
//
// Until now `mental-trigger` and `mental-copy` were only ever exercised by an eval: nothing in the
// running system called them, so no message could reach anyone. This wires the decision to the day the
// user is actually having — real calendar, real location, real send history — and refuses to invent any
// of those three. Everything it needs is injected, so the scheduler owns the I/O and this owns the rule.

const { evaluateMentalTrigger } = require("./mental-trigger.js");
const { buildMentalMessage } = require("./mental-copy.js");

function pickSeed(seeds, uid, trigger) {
  const list = (Array.isArray(seeds) ? seeds : []).filter((seed) => String(seed || "").trim());
  if (!list.length) return null;
  let hash = 0x811c9dc5;
  for (const character of `${uid}:${trigger}`) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return list[hash % list.length];
}

async function mentalUserOnce(user, nowMs, deps = {}) {
  if (!user || !user.uid || !user.telegram_chat_id) {
    return { decision: "suppress", reason: "unreachable" };
  }

  // A day we cannot read is not a day we may guess at: silence beats a message aimed at the wrong moment.
  let events;
  try {
    events = await deps.fetchUpcomingEvents(user.uid, { nowMs });
  } catch {
    return { decision: "suppress", reason: "calendar-unavailable" };
  }

  const [locationState, sendState] = await Promise.all([
    deps.getLocationState(user.uid, nowMs),
    deps.readSendState(user.uid, nowMs),
  ]);

  const verdict = evaluateMentalTrigger({
    nowMs,
    events: (Array.isArray(events) ? events : []).map((event) => ({
      startMs: event.startMs,
      endMs: event.endMs,
      important: Boolean(event.important),
      intense: Boolean(event.intense),
    })),
    sentTodayCount: Number(sendState && sendState.sentTodayCount) || 0,
    lastSentMs: sendState && Number.isFinite(sendState.lastSentMs) ? sendState.lastSentMs : null,
    sleepTargetMs: Number.isFinite(deps.sleepTargetMs) ? deps.sleepTargetMs : null,
    location: { state: locationState || "unknown" },
  });

  if (verdict.decision !== "send") return verdict;

  const seed = pickSeed(deps.seeds, user.uid, verdict.trigger);
  if (!seed) return { decision: "suppress", reason: "no-seed" };
  const text = buildMentalMessage({ trigger: verdict.trigger, seed });

  const response = await deps.sendMessage(deps.telegramToken, user.telegram_chat_id, text);
  const messageId = response && response.result && response.result.message_id;
  if (!response || !response.ok || messageId === undefined || messageId === null) {
    // Recording an undelivered line would corrupt both the daily cap and the evidence trail.
    return { ...verdict, delivered: false };
  }

  await deps.recordSend(user.uid, verdict.trigger, messageId);
  return { ...verdict, delivered: true, telegramMessageId: messageId };
}

module.exports = { mentalUserOnce, pickSeed };
