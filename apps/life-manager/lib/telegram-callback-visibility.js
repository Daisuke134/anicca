// lib/telegram-callback-visibility.js — CB-1 (spec §10.0-15): every inline-button tap must leave a
// durable, visible response in chat.
//
// Before this module, ask (オンライン/対面・はい) and payout (bank/wallet/later) callbacks wrote to
// the database and answered the callbackQuery toast — which vanishes in seconds — so the chat looked
// exactly as if nothing had happened, and the original keyboard stayed tappable forever. The ruling's
// contract: ① reflect the tapped choice on the original message and remove the keyboard, ② send a
// follow-up only when the flow continues, ③ a second tap gets a visible "already registered".
//
// These helpers implement ①. They are deliberately non-throwing: visibility is best-effort UX on top
// of an already-persisted answer, so a Telegram outage here must degrade to "toast only" rather than
// crash the webhook handler or roll back the persist. Every call carries a 15s abort signal so a
// hung Bot API cannot pin the handler open.
"use strict";

const DEFAULT_TIMEOUT_MS = 15_000;

async function editCall(token, method, body, opts = {}) {
  if (!token || !body.chat_id || !body.message_id) return { ok: false, reason: "unaddressable" };
  const f = opts.fetchImpl || fetch;
  const timeoutMs = opts.timeoutMs == null ? DEFAULT_TIMEOUT_MS : opts.timeoutMs;
  try {
    const response = await f(`https://api.telegram.org/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response || !response.ok) return { ok: false, status: response && response.status };
    const json = await response.json().catch(() => null);
    return json && json.ok ? { ok: true, result: json.result } : { ok: false };
  } catch (error) {
    return { ok: false, error: String((error && error.message) || error) };
  }
}

// markup === null means "remove the keyboard": the Bot API strips it when reply_markup is omitted.
function editMessageReplyMarkup(token, chatId, messageId, markup, opts = {}) {
  return editCall(token, "editMessageReplyMarkup", {
    chat_id: chatId, message_id: messageId,
    ...(markup == null ? {} : { reply_markup: markup }),
  }, opts);
}

// The visible "answered" state: the original question with the chosen label appended. No parse_mode —
// the webhook hands us the message text as plain text, so re-sending it plain is the only encoding
// that cannot mangle what the user already read. Omitting reply_markup removes the keyboard.
function markAnswered(token, chatId, messageId, originalText, chosenLabel, opts = {}) {
  if (!originalText) return Promise.resolve({ ok: false, reason: "no_original_text" });
  return editCall(token, "editMessageText", {
    chat_id: chatId, message_id: messageId,
    text: `${String(originalText)}\n\n→ ${String(chosenLabel || "")}`,
  }, opts);
}

// The one call sites should use: full markAnswered when the webhook carried the original text,
// otherwise at least strip the stale keyboard so the button cannot be tapped into silence again.
function reflectAnswer({ token, chatId, messageId, messageText, label, fetchImpl, timeoutMs } = {}) {
  const opts = { fetchImpl, timeoutMs };
  return messageText
    ? markAnswered(token, chatId, messageId, messageText, label, opts)
    : editMessageReplyMarkup(token, chatId, messageId, null, opts);
}

module.exports = { editMessageReplyMarkup, markAnswered, reflectAnswer };
