// lib/telegram-onboard.js — LM-6 minimal-question Telegram onboarding.
"use strict";

const { sendMessage, onboardLink } = require("./telegram.js");
const { signedGmailConnectUrl } = require("./gmail-onboard.js");
const { backfillCalendarContext } = require("./context-graph.js");
const { mailAvailable } = require("./mail-availability.js");

// PURE: calendar/pay are taps, phone is the only typed question, and Gmail is skippable after pay.
function computeStage(row) {
  if (!row || row.calendar_provider !== "composio_gcal") return "calendar";
  if (!row.phone) return "phone";
  if (row.paid !== true) return "pay";
  if (!row.gmail_account_id && row.gmail_skipped !== true) return "gmail";
  return "done";
}

function telegramProfileName(from) {
  if (!from) return "";
  return [from.first_name, from.last_name].map((part) => String(part || "").trim()).filter(Boolean).join(" ").slice(0, 120);
}

function applyTelegramProfileName(row, from) {
  const current = row ? { ...row } : {};
  if (!current.name) {
    const name = telegramProfileName(from);
    if (name) current.name = name;
  }
  return current;
}

const NATIVE_STAGES = new Set(["phone"]);
const isNativeStage = (stage) => NATIVE_STAGES.has(stage);

function normalizePhone(text) {
  let value = String(text || "").replace(/[^\d+]/g, "");
  if (!value.startsWith("+")) value = "+" + value.replace(/^0+/, "");
  return /^\+[1-9]\d{7,14}$/.test(value) ? value : null;
}

function stageMessage(stage, chatId, base, gmailConnectUrl, profileName) {
  let link = onboardLink(chatId, base);
  if (profileName) link += `&name=${encodeURIComponent(profileName)}`;
  const urlButton = (text, url = link) => ({ reply_markup: { inline_keyboard: [[{ text, url }]] } });
  switch (stage) {
    case "calendar":
      return { text: "👋 <b>Welcome to Life Manager!</b>\n\nConnect your Google Calendar (10 sec). Tap below, sign in, then come back here.", extra: urlButton("📅 Connect Calendar") };
    case "phone":
      return { text: "✅ <b>Calendar connected!</b>\n\nWhat's your phone number? Type it with the country code, e.g. <code>+818012345678</code> — I'll call you before events.", extra: undefined };
    case "pay":
      return { text: "✅ <b>Phone saved!</b>\n\nSubscribe ($20/mo) and I'll take it from here.", extra: urlButton("⭐ Subscribe") };
    case "gmail": {
      const connectUrl = gmailConnectUrl || `${link}&gmail=connect`;
      return {
        text: "Optional: connect Gmail so I can use relevant email context. You can skip this and every Gmail-independent feature will still work.",
        extra: { reply_markup: { inline_keyboard: [[
          { text: "✉️ Connect Gmail", url: connectUrl }, { text: "Skip", callback_data: "gmail:skip" },
        ]] } },
      };
    }
    case "done":
      return { text: "🎉 <b>You're all set!</b>\n\nI'll now manage your schedule — I call you before you must leave, fill in travel time, and only ask when I genuinely can't find a location. Talk soon.", extra: undefined };
    default:
      return { text: "Tap below to continue setting up Life Manager.", extra: urlButton("Open Life Manager") };
  }
}

async function sendStage(token, chatId, row, base, opts = {}) {
  const effective = applyTelegramProfileName(row, opts.profile || null);
  let stage = computeStage(effective);
  if (stage === "gmail") {
    const available = await (opts.mailAvailable || mailAvailable)(effective, opts.mailOptions || {});
    if (!available) {
      await (opts.saveField || saveField)(effective.uid, { gmail_skipped: true }, opts.supaUrl, opts.supaKey);
      await (opts.sendMessage || sendMessage)(token, chatId,
        "✉️ Gmail integration is currently being prepared, so I skipped that optional step. Your Calendar and all Gmail-independent features are ready.");
      return "done";
    }
  }
  const message = stageMessage(stage, chatId, base, opts.gmailConnectUrl, effective.name);
  await (opts.sendMessage || sendMessage)(token, chatId, message.text, message.extra);
  return stage;
}

const SEL = "uid,name,telegram_chat_id,tg_onboard_stage,calendar_provider,gmail_account_id,gmail_skipped,email,phone,paid";
async function saveField(uid, patch, supaUrl, supaKey) {
  await fetch(`${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ ...patch, updated_at: new Date().toISOString() }),
  }).catch(() => {});
}
async function rowByChatId(chatId, supaUrl, supaKey) {
  const response = await fetch(`${supaUrl}/rest/v1/lm_users?telegram_chat_id=eq.${encodeURIComponent(chatId)}&select=${SEL}&limit=1`,
    { headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` } });
  const data = await response.json().catch(() => []);
  return Array.isArray(data) && data[0] ? data[0] : null;
}
async function linkedRows(supaUrl, supaKey) {
  const response = await fetch(`${supaUrl}/rest/v1/lm_users?telegram_chat_id=not.is.null&select=${SEL}`,
    { headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` } });
  const data = await response.json().catch(() => []);
  return Array.isArray(data) ? data : [];
}
async function setStage(uid, stage, supaUrl, supaKey) {
  await fetch(`${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ tg_onboard_stage: stage }),
  }).catch(() => {});
}

async function backfillIfCalendarCompleted(row, opts = {}) {
  if (!row || row.tg_onboard_stage !== "calendar" || computeStage(row) === "calendar") return false;
  const backfill = opts.backfillCalendarContext || backfillCalendarContext;
  await backfill(row.uid, {
    composioKey: opts.composioKey, geminiKey: opts.geminiKey,
    supaUrl: opts.supaUrl, supaKey: opts.supaKey, gmailAccountId: row.gmail_account_id,
  });
  return true;
}

async function handleOnboardingText(chatId, text, row, opts) {
  const stage = computeStage(row);
  await backfillIfCalendarCompleted(row, opts);
  if (stage === "phone") {
    const phone = normalizePhone(text);
    if (!phone) {
      await sendMessage(opts.token, chatId, "That doesn't look like a phone number. Please type it with the country code, e.g. <code>+818012345678</code>.");
      return "bad-phone";
    }
    await saveField(row.uid, { phone }, opts.supaUrl, opts.supaKey);
    const next = computeStage({ ...row, phone });
    const message = stageMessage(next, chatId, opts.base);
    await sendMessage(opts.token, chatId, message.text, message.extra);
    await setStage(row.uid, next, opts.supaUrl, opts.supaKey);
    return "phone";
  }
  if (stage === "done") return "done";
  await sendStage(opts.token, chatId, row, opts.base, opts);
  if (row) await setStage(row.uid, stage, opts.supaUrl, opts.supaKey);
  return "guidance";
}

async function handleGmailCallback(data, row, opts = {}) {
  if (data !== "gmail:skip") return { ok: false, ignored: true };
  if (!row || !row.uid) return { ok: false, reason: "unlinked_chat" };
  const save = opts.saveField || saveField;
  const persistStage = opts.setStage || setStage;
  const send = opts.sendMessage || sendMessage;
  await save(row.uid, { gmail_skipped: true }, opts.supaUrl, opts.supaKey);
  const stage = computeStage({ ...row, gmail_skipped: true });
  const message = stageMessage(stage, opts.chatId || row.telegram_chat_id, opts.base);
  await send(opts.token, opts.chatId || row.telegram_chat_id, message.text, message.extra);
  await persistStage(row.uid, stage, opts.supaUrl, opts.supaKey);
  return { ok: true, stage };
}

async function onboardNudgeAll(opts) {
  if (!opts.token || !opts.supaUrl || !opts.supaKey) return 0;
  const list = opts.linkedRows || linkedRows;
  const announce = opts.sendStage || sendStage;
  const persistStage = opts.setStage || setStage;
  const backfill = opts.backfillCalendarContext || backfillCalendarContext;
  const rows = await list(opts.supaUrl, opts.supaKey);
  let sent = 0;
  for (const row of rows) {
    let stage = computeStage(row);
    if (stage === "gmail") {
      const available = await (opts.mailAvailable || mailAvailable)(row, opts.mailOptions || {});
      if (!available) {
        await (opts.saveField || saveField)(row.uid, { gmail_skipped: true }, opts.supaUrl, opts.supaKey);
        await (opts.sendMessage || sendMessage)(opts.token, row.telegram_chat_id,
          "✉️ Gmail integration is currently being prepared, so I skipped that optional step. Your Calendar and all Gmail-independent features are ready.");
        stage = "done";
        await persistStage(row.uid, stage, opts.supaUrl, opts.supaKey);
        sent++;
        continue;
      }
    }
    if (stage === row.tg_onboard_stage) continue;
    await backfillIfCalendarCompleted(row, { ...opts, backfillCalendarContext: backfill });
    const gmailConnectUrl = opts.gmailConfigured === false
      ? "" : signedGmailConnectUrl(row.uid, opts.gmailBase, opts.uidSecret);
    await announce(opts.token, row.telegram_chat_id, row, opts.base, { gmailConnectUrl });
    await persistStage(row.uid, stage, opts.supaUrl, opts.supaKey);
    sent++;
  }
  return sent;
}

module.exports = {
  computeStage, telegramProfileName, applyTelegramProfileName, stageMessage, sendStage, isNativeStage,
  normalizePhone, handleOnboardingText, handleGmailCallback, rowByChatId, linkedRows, setStage,
  saveField, backfillIfCalendarCompleted, onboardNudgeAll,
};
