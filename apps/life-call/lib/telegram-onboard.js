// lib/telegram-onboard.js — interactive Telegram onboarding: the bot guides the user one step at a
// time and acknowledges each, driven purely by their lm_users row state.
"use strict";

const { sendMessage, onboardLink } = require("./telegram.js");

// PURE: the onboarding stage is a function of the row. A null/!linked row starts at "calendar".
// Order: calendar → gmail → phone → pay → done.
function computeStage(row) {
  if (!row) return "calendar";
  if (row.paid === true) return "done";
  if (row.calendar_provider !== "composio_gcal") return "calendar";
  if (!row.gmail_account_id) return "gmail";
  if (!row.phone) return "phone";
  return "pay"; // has calendar+gmail+phone but not paid
}

// PURE: the message + inline button for a stage. base = public web origin.
function stageMessage(stage, chatId, base) {
  const link = onboardLink(chatId, base); // /lm?tg=<chat_id> — page resumes at the right step
  const btn = (text) => ({ reply_markup: { inline_keyboard: [[{ text, url: link }]] } });
  switch (stage) {
    case "calendar":
      return { text: "👋 <b>Let's set up Life Manager.</b>\n\nStep 1 — connect your Google Calendar so I can see your schedule and call you before you need to leave.", extra: btn("📅 Connect Calendar") };
    case "gmail":
      return { text: "✅ <b>Calendar connected!</b>\n\nStep 2 — connect Gmail so I can ask about events and act on your behalf.", extra: btn("📧 Connect Gmail") };
    case "phone":
      return { text: "✅ <b>Gmail connected!</b>\n\nStep 3 — add your phone number so I can call you before events.", extra: btn("📱 Add phone") };
    case "pay":
      return { text: "✅ <b>Phone saved!</b>\n\nLast step — subscribe ($20/mo) and I'll take it from here.", extra: btn("⭐ Subscribe & finish") };
    case "done":
      return { text: "🎉 <b>You're all set!</b>\n\nI'll now manage your schedule — I call you before you must leave, fill in travel time, and only ask when I genuinely can't find a location. Talk soon." , extra: undefined };
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
const SEL = "uid,telegram_chat_id,tg_onboard_stage,calendar_provider,gmail_account_id,phone,paid";
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

module.exports = { computeStage, stageMessage, sendStage, rowByChatId, linkedRows, setStage, onboardNudgeAll };
