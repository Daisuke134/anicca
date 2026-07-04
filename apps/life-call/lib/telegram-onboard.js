// lib/telegram-onboard.js — interactive Telegram onboarding: the bot guides the user one step at a
// time and acknowledges each, driven purely by their lm_users row state.
"use strict";

const { sendMessage, onboardLink } = require("./telegram.js");

// PURE: the onboarding stage is a function of the row. Same ORDER as the web app
// (name → calendar → gmail → phone → pay → done). On Telegram, name + phone are collected NATIVELY in
// chat (no web needed); calendar/pay need the web (OAuth/Stripe). A null row starts at "name".
// v1 (Dais 2026-06-25): Telegram is the ask/reply channel, so TG users do NOT connect Gmail — the gmail
// stage is dropped. Flow = name → calendar → phone → pay → done. (Web onboarding's email loop is v1.5.)
function computeStage(row) {
  if (!row || !row.name) return "name";
  if (row.calendar_provider !== "composio_gcal") return "calendar";
  if (!row.phone) return "phone";
  if (row.paid !== true) return "pay";
  return "done";
}

// Native (typed-in-chat) stages vs web-link stages.
const NATIVE_STAGES = new Set(["name", "phone"]);
const isNativeStage = (stage) => NATIVE_STAGES.has(stage);

// Normalize a typed phone to E.164-ish; return null if it can't be a valid number.
function normalizePhone(text) {
  let s = String(text || "").replace(/[^\d+]/g, "");
  if (!s.startsWith("+")) s = "+" + s.replace(/^0+/, "");
  return /^\+[1-9]\d{7,14}$/.test(s) ? s : null;
}

// PURE: the message for a stage. Native stages (name/phone) are questions with no button — the user
// just types. Web stages carry a button to /lm?tg=<chat_id>.
function stageMessage(stage, chatId, base) {
  const link = onboardLink(chatId, base); // /lm?tg=<chat_id> — page resumes at the right step
  const btn = (text) => ({ reply_markup: { inline_keyboard: [[{ text, url: link }]] } });
  switch (stage) {
    case "name":
      return { text: "👋 <b>Welcome to Life Manager!</b>\n\nFirst — what's your name? Just type it here.", extra: undefined };
    case "calendar":
      return { text: "Next — connect your Google Calendar (10 sec). Tap below: it opens your browser for a quick Google sign-in, then just come back to this chat — I'll pick up automatically.", extra: btn("📅 Connect Calendar") };
    case "phone":
      return { text: "✅ <b>Calendar connected!</b>\n\nWhat's your phone number? Type it with the country code, e.g. <code>+818012345678</code> — I'll call you before events.", extra: undefined };
    case "pay":
      return { text: "✅ <b>Phone saved!</b>\n\nLast step — subscribe ($20/mo) and I'll take it from here.", extra: btn("⭐ Subscribe & finish") };
    case "done":
      return { text: "🎉 <b>You're all set!</b>\n\nI'll now manage your schedule — I call you before you must leave, fill in travel time, and only ask when I genuinely can't find a location. Talk soon.", extra: undefined };
    default:
      return { text: "Tap below to continue setting up Life Manager.", extra: btn("Open Life Manager") };
  }
}

// Send the current stage's message to a chat (used by /start and the on-message guidance path).
async function sendStage(token, chatId, row, base) {
  const stage = computeStage(row);
  const m = stageMessage(stage, chatId, base);
  await sendMessage(token, chatId, m.text, m.extra);
  return stage;
}

// ── Supabase helpers ────────────────────────────────────────────────────────────
const SEL = "uid,name,telegram_chat_id,tg_onboard_stage,calendar_provider,gmail_account_id,email,phone,paid";
// Persist a single onboarding field (name/phone) typed in chat.
async function saveField(uid, patch, supaUrl, supaKey) {
  await fetch(`${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ ...patch, updated_at: new Date().toISOString() }),
  }).catch(() => {});
}
async function rowByChatId(chatId, supaUrl, supaKey) {
  const r = await fetch(`${supaUrl}/rest/v1/lm_users?telegram_chat_id=eq.${encodeURIComponent(chatId)}&select=${SEL}&limit=1`,
    { headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` } });
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}
async function linkedRows(supaUrl, supaKey) {
  const r = await fetch(`${supaUrl}/rest/v1/lm_users?telegram_chat_id=not.is.null&select=${SEL}`,
    { headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` } });
  const d = await r.json().catch(() => []);
  return Array.isArray(d) ? d : [];
}
async function setStage(uid, stage, supaUrl, supaKey) {
  await fetch(`${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ tg_onboard_stage: stage }),
  }).catch(() => {});
}

// Handle a free-text message during onboarding. Native stages (name/phone) capture the typed value;
// web stages re-nudge; "done" tells the caller to treat the text as a location reply instead.
// Returns one of: "name" | "phone" | "bad-phone" | "guidance" | "done".
async function handleOnboardingText(chatId, text, row, { token, base, supaUrl, supaKey }) {
  const stage = computeStage(row);
  if (stage === "name") {
    const name = String(text || "").trim().slice(0, 80);
    if (!name) { await sendMessage(token, chatId, "Please type your name 🙂"); return "name"; }
    if (row) {
      await saveField(row.uid, { name }, supaUrl, supaKey);
      const next = computeStage({ ...row, name });
      await sendMessage(token, chatId, `Nice to meet you, <b>${name}</b>! 🎉`);
      const m = stageMessage(next, chatId, base);
      await sendMessage(token, chatId, m.text, m.extra);
      await setStage(row.uid, next, supaUrl, supaKey);
    } else {
      // Not linked yet — carry the name in the connect link so the web saves it when binding.
      const root = (base || "https://aniccaai.com").replace(/\/$/, "");
      const link = `${root}/lm?tg=${encodeURIComponent(chatId)}&name=${encodeURIComponent(name)}`;
      await sendMessage(token, chatId, `Nice to meet you, <b>${name}</b>! 🎉\n\nNext — connect your Google Calendar (10 sec). Tap below: it opens your browser for a quick Google sign-in, then come back here.`,
        { reply_markup: { inline_keyboard: [[{ text: "📅 Connect Calendar", url: link }]] } });
    }
    return "name";
  }
  if (stage === "phone") {
    const phone = normalizePhone(text);
    if (!phone) {
      await sendMessage(token, chatId, "That doesn't look like a phone number. Please type it with the country code, e.g. <code>+818012345678</code>.");
      return "bad-phone";
    }
    await saveField(row.uid, { phone }, supaUrl, supaKey);
    const next = computeStage({ ...row, phone });
    const m = stageMessage(next, chatId, base);
    await sendMessage(token, chatId, m.text, m.extra);
    await setStage(row.uid, next, supaUrl, supaKey);
    return "phone";
  }
  if (stage === "done") return "done"; // caller routes the text to the location-reply path
  // calendar / gmail / pay → just re-show the current step (tap the button).
  await sendStage(token, chatId, row, base);
  if (row) await setStage(row.uid, stage, supaUrl, supaKey);
  return "guidance";
}

// Proactive nudge: for every linked user, if their computed stage changed since we last announced it,
// send the new stage's message and persist it. Idempotent — a stage is announced once. Returns count.
async function onboardNudgeAll({ token, base, supaUrl, supaKey }) {
  if (!token || !supaUrl || !supaKey) return 0;
  const rows = await linkedRows(supaUrl, supaKey);
  let sent = 0;
  for (const row of rows) {
    const stage = computeStage(row);
    if (stage === row.tg_onboard_stage) continue; // already announced this stage
    await sendStage(token, row.telegram_chat_id, row, base);
    await setStage(row.uid, stage, supaUrl, supaKey);
    sent++;
  }
  return sent;
}

module.exports = { computeStage, stageMessage, sendStage, isNativeStage, normalizePhone, handleOnboardingText, rowByChatId, linkedRows, setStage, saveField, onboardNudgeAll };
