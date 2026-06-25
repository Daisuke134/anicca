// lib/telegram-reply.js — turn a free-text Telegram reply into a calendar location update.
//
// Mirrors the email reply path (ask.js READ phase) but for Telegram: find the user by their
// telegram_chat_id, list their events still missing a location, let Gemini match the reply to the
// right one (agentMatchReply — no regex), and patch the real calendar via Composio.
"use strict";

const { agentMatchReply } = require("./ask.js");
const { getCalendar } = require("./transport/index.js");
const { placeKey, rememberPlace } = require("./places-memory.js");

async function userByChatId(chatId) {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  const r = await fetch(
    `${url}/rest/v1/lm_users?telegram_chat_id=eq.${encodeURIComponent(chatId)}&select=uid,calendar_provider,paid&limit=1`,
    { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}

function needsLocation(e) {
  const s = (e.summary || "").trim();
  if (s.startsWith("[Travel]") || s.startsWith("[Ask]")) return false;
  if (!((e.start || {}).dateTime)) return false;
  return !((e.location || "").trim());
}

// Returns { filled, event, location }.
async function resolveTelegramReply(chatId, text) {
  const composioKey = process.env.COMPOSIO_API_KEY, geminiKey = process.env.GEMINI_API_KEY;
  const out = { filled: false, event: "", location: "" };
  if (!composioKey || !geminiKey) return out;
  const user = await userByChatId(chatId);
  if (!user || user.calendar_provider !== "composio_gcal") return out;

  const now = Date.now();
  const items = await getCalendar({ apiKey: composioKey }).listEventsRaw(user.uid, {
    timeMin: new Date(now).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(now + 7 * 86400 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
    maxResults: 50,
  });
  const pending = items.filter(needsLocation);
  if (!pending.length) return out;

  const match = await agentMatchReply(text, pending.map((e) => ({ id: e.id, summary: e.summary })), geminiKey);
  if (!match) return out;
  const ev = pending.find((e) => e.id === match.eventId);
  if (!ev) return out;
  await getCalendar({ apiKey: composioKey }).patchEvent(user.uid, { calendar_id: "primary", event_id: ev.id, location: match.location });
  // PC-1 (C3 REQ-46): remember so a future same-summary event autofills without re-asking.
  await rememberPlace(user.uid, placeKey(ev.summary), match.location, process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  return { filled: true, event: ev.summary || "your event", location: match.location };
}

module.exports = { resolveTelegramReply, userByChatId };
