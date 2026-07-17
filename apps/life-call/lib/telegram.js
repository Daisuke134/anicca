// lib/telegram.js — Life Manager Telegram bot helpers (raw Bot API, no SDK dependency).
//
// Uses LM_TELEGRAM_BOT_TOKEN — the DEDICATED Life Manager bot (created by Dais via @BotFather),
// distinct from OpenClaw's personal @AniccaLifeBot. Webhook updates land on life-call POST /telegram.
"use strict";

const TG = (token) => `https://api.telegram.org/bot${token}`;

async function tgCall(token, method, body) {
  try {
    const r = await fetch(`${TG(token)}/${method}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return await r.json();
  } catch (e) { return { ok: false, error: String(e) }; }
}

const sendMessage = (token, chatId, text, extra) =>
  tgCall(token, "sendMessage", { chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true, ...(extra || {}) });

const getMe = (token) => tgCall(token, "getMe");

// Register the webhook with a secret token Telegram echoes back in a header we verify on each update.
const setWebhook = (token, url, secret) =>
  tgCall(token, "setWebhook", { url, secret_token: secret, allowed_updates: ["message", "callback_query"] });

const answerCallbackQuery = (token, id, text) =>
  tgCall(token, "answerCallbackQuery", { callback_query_id: id, ...(text ? { text } : {}) });

// Pull the meaningful bits out of a Telegram update. Message fields remain backward-compatible.
function parseUpdate(update) {
  const q = update && update.callback_query;
  if (q && q.message && q.message.chat) {
    return {
      kind: "callback",
      chatId: String(q.message.chat.id),
      userId: q.from ? String(q.from.id) : "",
      data: String(q.data || ""),
      callbackQueryId: String(q.id || ""),
    };
  }
  const m = update && update.message;
  if (!m || !m.chat) return null;
  return {
    kind: "message",
    chatId: String(m.chat.id),
    userId: m.from ? String(m.from.id) : "",
    text: (m.text || "").trim(),
    isStart: (m.text || "").trim().toLowerCase().startsWith("/start"),
  };
}

async function routeCallbackData(data, handlers = {}, log = console.log) {
  const prefix = String(data || "").split(":", 1)[0];
  if (prefix === "ask" && typeof handlers.ask === "function") return handlers.ask(data);
  log(`[telegram] ignoring unknown callback prefix: ${String(data || "").slice(0, 40)}`);
  return { ignored: true };
}

// The onboarding deep link: Telegram can't host Google OAuth or Stripe, so /start hands the user to
// the web /lm flow, carrying the chat id so the web side can store it on the lm_users row.
function onboardLink(chatId, base) {
  const root = (base || "https://aniccaai.com").replace(/\/$/, "");
  return `${root}/lm?tg=${encodeURIComponent(chatId)}`;
}

// The /start reply: a button to the web onboarding.
function startReply(chatId, base) {
  return {
    text:
      "👋 <b>Anicca Life Manager</b>\n\n" +
      "I keep you on time — I call you before you must leave, fill in travel time, ask where events are, " +
      "and handle late-notices. Set up takes a minute: connect Google Calendar, add your phone, subscribe.\n\n" +
      "Tap below to start 👇",
    extra: {
      reply_markup: {
        inline_keyboard: [[{ text: "🚀 Set up Life Manager", url: onboardLink(chatId, base) }]],
      },
    },
  };
}

module.exports = { tgCall, sendMessage, getMe, setWebhook, answerCallbackQuery, parseUpdate, routeCallbackData, onboardLink, startReply };
