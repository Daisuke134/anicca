// lib/slash-command.js — spec §12.1 row 4: the generic slash-command router for the LM Telegram bot.
//
// The legacy telegram_bot.py understood /start /help /status /where /stop /subscribe /connect
// /payout /reset (plus the live-location stream). LM's webhook only routed /start and /panel; every
// other /command fell through to the onboarding text handler and was answered with a setup nudge —
// dishonest routing. This module closes that gap:
//
//   parseSlashCommand  — recognises any /command (optional @BotName suffix, optional args)
//   slashAliasText     — /connect maps onto the SAME parsed-control flow as the natural-language
//                        "connect calendar" (Gmail stays intentionally OFF, so calendar only)
//   handleSlashCommand — /help /status /where /stop /subscribe /payout /reset are handled here with
//                        injected deps; /start and /panel PASS THROUGH untouched (their existing
//                        server.js branches stay the owner); an unknown /command gets an honest
//                        "unknown command" reply instead of an onboarding/feedback/browser-task
//                        misroute.
//
// HONESTY RULES carried over from the payout/feedback siblings: every reply is built only from data
// this process actually read (a location column that does not exist — accuracy — is never invented),
// a store operation we could not confirm is reported as a failure, and the reply for "nothing stored"
// says so instead of dressing up a no-op as a delete.
"use strict";

const { sendMessage, onboardLink } = require("./telegram.js");
const { parseUserCommand } = require("./user-command.js");
const { getLiveLocation, deleteLiveLocation } = require("./late-notice.js");
const { computeStage, setStage } = require("./telegram-onboard.js");
const { askPayoutQuestion } = require("./payout-question.js");

// Every /command this bot understands. start/panel are listed for /help but owned elsewhere.
const KNOWN_COMMANDS = Object.freeze([
  "start", "panel", "help", "status", "where", "stop", "subscribe", "connect", "payout", "reset",
]);
const PASSTHROUGH = new Set(["start", "panel"]);
// The slash aliases that re-enter the existing parsed-control flow instead of being handled here.
const NL_ALIASES = Object.freeze({ connect: "connect calendar" });

function parseSlashCommand(text) {
  const value = String(text || "").trim();
  const match = /^\/([A-Za-z0-9_]+)(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/.exec(value);
  if (!match) return null;
  return { name: match[1].toLowerCase(), args: String(match[2] || "").trim() };
}

function slashAliasText(parsed) {
  return (parsed && NL_ALIASES[parsed.name]) || null;
}

function helpMessage() {
  // kind:"help" wiring: parseUserCommand computes availableActions for unrecognised text; server.js
  // used to drop them. /help is where that computation finally reaches the user.
  const help = parseUserCommand("");
  return [
    "Commands:",
    "  /start — begin (or resume) onboarding",
    "  /panel — open your dashboard panel",
    "  /help — this message",
    "  /status — your Life Manager health snapshot",
    "  /where — show the live location I currently know",
    "  /stop — delete your stored live location",
    "  /subscribe — get the subscription link",
    "  /connect — connect Google Calendar",
    "  /payout — set or change your payout destination",
    "  /reset — restart the onboarding announcements",
    "",
    "You can also type:",
    ...help.availableActions.map((action) => `  ${action}`),
  ].join("\n");
}

function setupFirstMessage(name) {
  return `Complete Life Manager setup with /start before using /${name}.`;
}

function coarseCoord(value) {
  return Number(value).toFixed(2);
}

function secondsAgo(iso, nowMs) {
  return Math.max(0, Math.round((nowMs - Date.parse(iso)) / 1000));
}

function minutesUntil(iso, nowMs) {
  return Math.max(0, Math.ceil((Date.parse(iso) - nowMs) / 60_000));
}

// Privacy-safe: coordinates rounded to ~1km, no full-precision echo into chat history, and no
// accuracy field — the lm_user_locations schema does not store one, so we never fabricate it.
function whereMessage(location, nowMs) {
  return [
    "📍 Last live fix (rounded to ~1km):",
    `  lat: ${coarseCoord(location.latitude)}`,
    `  lon: ${coarseCoord(location.longitude)}`,
    `  observed: ${secondsAgo(location.observed_at, nowMs)}s ago`,
    `  expires: in ${minutesUntil(location.expires_at, nowMs)} min`,
  ].join("\n");
}

const NO_LOCATION_MESSAGE =
  "I don't have a fresh live location for you. Share Live Location in Telegram and I'll track it.";

function payoutStatusLine(destination) {
  if (!destination || typeof destination !== "object") return "not set";
  if (destination.status === "usable" || destination.status === "ready") return "registered";
  if (destination.status === "awaiting_address") return "awaiting typed address";
  if (destination.status === "awaiting_details") return "rail chosen, awaiting details";
  return "unknown";
}

// The health snapshot is a projection of what the webhook can actually read: the lm_users row it was
// handed and one live-location read. Legacy /status also reported cron/last-call health; those live
// in stores this HTTP path cannot cheaply reach, so they are OMITTED rather than fabricated.
function statusMessage(row, location, nowMs) {
  const stage = computeStage(row);
  return [
    "🩺 Life Manager status",
    stage === "done" ? "🚀 Onboarding: done" : `🚀 Onboarding: at the "${stage}" step`,
    `📅 Calendar: ${row.calendar_provider === "composio_gcal" ? "connected" : "not connected"}`,
    `📱 Phone: ${row.phone ? "on file" : "not set"}`,
    `⭐ Subscription: ${row.paid === true ? "active" : "not active"}`,
    `💸 Payout: ${payoutStatusLine(row.payout_destination)}`,
    location
      ? `📍 Location: fresh (observed ${secondsAgo(location.observed_at, nowMs)}s ago)`
      : "📍 Location: not available (share Live Location in Telegram)",
  ].join("\n");
}

async function handleSlashCommand(parsed, row, deps = {}) {
  if (!parsed || PASSTHROUGH.has(parsed.name)) return { handled: false };
  const name = parsed.name;
  const send = deps.send || sendMessage;
  const log = deps.log || console.log;
  const nowMs = deps.nowMs == null ? Date.now() : deps.nowMs;
  const chatId = String(deps.chatId || "");

  if (!KNOWN_COMMANDS.includes(name)) {
    await send(deps.token, chatId, `Unknown command: /${name}. Send /help to see what I understand.`);
    return { handled: true, action: "unknown" };
  }

  if (name === "help") {
    await send(deps.token, chatId, helpMessage());
    return { handled: true, action: "help" };
  }

  if (name === "subscribe") {
    if (row && row.paid === true) {
      await send(deps.token, chatId, "⭐ Your Life Manager subscription is already active.");
      return { handled: true, action: "subscribe", ok: true, alreadyActive: true };
    }
    // Reuse the existing onboard link builder — the web /lm flow hosts the Stripe checkout. No URL
    // is invented here; without a chat id there is no link to build, and we say so.
    if (!chatId) {
      await send(deps.token, chatId, "The subscription link is unavailable right now. Please try again shortly.");
      return { handled: true, action: "subscribe", ok: false, reason: "link_unavailable" };
    }
    await send(deps.token, chatId,
      "⭐ <b>Life Manager</b> — $20/mo, cancel anytime. I call you before you must leave, fill in travel time, and handle late notices.\n\nTap below to subscribe 👇",
      { reply_markup: { inline_keyboard: [[{ text: "⭐ Subscribe", url: onboardLink(chatId, deps.base) }]] } });
    return { handled: true, action: "subscribe", ok: true };
  }

  // Everything below reads or mutates THIS user's account and needs the linked row.
  if (!row || !row.uid) {
    await send(deps.token, chatId, setupFirstMessage(name));
    return { handled: true, action: name, ok: false, reason: "unlinked" };
  }

  if (name === "where") {
    const location = await (deps.getLiveLocation || ((uid) => getLiveLocation(uid, nowMs, deps)))(row.uid);
    if (!location) {
      await send(deps.token, chatId, NO_LOCATION_MESSAGE);
      return { handled: true, action: "where", ok: true, stored: false };
    }
    await send(deps.token, chatId, whereMessage(location, nowMs));
    return { handled: true, action: "where", ok: true };
  }

  if (name === "stop") {
    const outcome = await (deps.deleteLiveLocation || ((uid) => deleteLiveLocation(uid, deps)))(row.uid);
    // Audit names the decision and the outcome, never the coordinates.
    log(`[location] /stop uid=${String(row.uid).slice(0, 12)} deleted=${outcome ? outcome.deleted : "error"}`);
    if (!outcome) {
      await send(deps.token, chatId, "I couldn't delete your stored location. Please try again.");
      return { handled: true, action: "stop", ok: false, reason: "delete_failed" };
    }
    await send(deps.token, chatId, outcome.deleted > 0
      ? "Stopped. Your stored live location was deleted. Share Live Location again any time to resume."
      : "You had no stored live location. Nothing was deleted.");
    return { handled: true, action: "stop", ok: true, deleted: outcome.deleted };
  }

  if (name === "reset") {
    // Restart the onboarding announcements: the stage itself is COMPUTED from the row's real data
    // (calendar/phone/paid), so /reset never wipes those — it rewinds the announced stage so /start
    // and the nudge loop re-walk the flow from the beginning.
    await (deps.setStage || setStage)(row.uid, "calendar", deps.supaUrl, deps.supaKey);
    await send(deps.token, chatId, "Onboarding announcements were reset. Send /start to walk through setup again.");
    return { handled: true, action: "reset", ok: true };
  }

  if (name === "payout") {
    // askPayoutQuestion is the idempotence: it reads payout_destination first, replies "already
    // registered" itself when one exists, and only then re-opens the picker — so /payout can never
    // stack a second pending question flow on top of the callback one.
    const outcome = await (deps.askPayoutQuestion || askPayoutQuestion)({
      uid: row.uid, chatId, token: deps.token,
      supaUrl: deps.supaUrl, supaKey: deps.supaKey, sendMessage: send,
    });
    log(`[payout] slash reopen asked=${outcome.asked}${outcome.reason ? ` reason=${outcome.reason}` : ""}`);
    if (outcome.asked || outcome.reason === "already_answered") {
      return { handled: true, action: "payout", ok: true, ...outcome };
    }
    await send(deps.token, chatId, "I couldn't open the payout registration right now. Please try again shortly.");
    return { handled: true, action: "payout", ok: false, ...outcome };
  }

  // /status
  const location = await (deps.getLiveLocation || ((uid) => getLiveLocation(uid, nowMs, deps)))(row.uid);
  await send(deps.token, chatId, statusMessage(row, location, nowMs));
  return { handled: true, action: "status", ok: true };
}

module.exports = {
  KNOWN_COMMANDS,
  parseSlashCommand,
  slashAliasText,
  helpMessage,
  handleSlashCommand,
};
