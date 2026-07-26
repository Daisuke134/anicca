// lib/webhook-selfheal.js — INC-3's permanent fix: the runtime registers its own webhook at boot.
//
// The incident class this kills: the registered secret and the runtime secret drifting apart
// (INC-1: staged env rolled under an old registration; INC-3: registration vanished entirely, then
// a re-registration was cut to 40 of 64 chars by a truncating table display). When the SAME process
// that will compare `x-telegram-bot-api-secret-token` also sends that value to setWebhook, there is
// nothing left to drift: both sides are one process.env read.
//
// Idempotent: getWebhookInfo first; setWebhook only when url or allowed_updates differ. Telegram
// cannot echo the registered secret back, so a mismatched-secret-but-matching-url state is healed
// lazily — the /telegram handler's 401s surface in getWebhookInfo.last_error_message, which is
// treated as a mismatch signal on the next boot.
"use strict";

const ALLOWED_UPDATES = ["message", "edited_message", "callback_query"]; // U4: live location arrives as edited_message

async function selfHealWebhook(env, deps = {}) {
  const fetchImpl = deps.fetchImpl || fetch;
  const token = String((env && env.LM_TELEGRAM_BOT_TOKEN) || "");
  const secret = String((env && env.LM_TELEGRAM_WEBHOOK_SECRET) || "");
  const base = String((env && env.LM_PUBLIC_URL) || "https://life-call-production.up.railway.app");
  if (!token) return { healed: false, reason: "no bot token in env" };
  if (!secret) return { healed: false, reason: "no webhook secret in env — refusing to register a blank secret" };
  const target = `${base.replace(/\/$/, "")}/telegram`;

  let info;
  try {
    const res = await fetchImpl(`https://api.telegram.org/bot${token}/getWebhookInfo`);
    info = await res.json();
  } catch (e) {
    return { healed: false, reason: `getWebhookInfo failed: ${e && e.message}` };
  }
  const current = (info && info.result) || {};
  const sameUrl = current.url === target;
  const sameUpdates = Array.isArray(current.allowed_updates)
    && ALLOWED_UPDATES.every((u) => current.allowed_updates.includes(u))
    && current.allowed_updates.length === ALLOWED_UPDATES.length;
  const authBroken = /unauthorized/i.test(String(current.last_error_message || ""));
  if (sameUrl && sameUpdates && !authBroken) return { healed: false, reason: "already-registered" };

  const body = new URLSearchParams({
    url: target,
    secret_token: secret,
    allowed_updates: JSON.stringify(ALLOWED_UPDATES),
  }).toString();
  let set;
  try {
    const res = await fetchImpl(`https://api.telegram.org/bot${token}/setWebhook`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body,
    });
    set = await res.json();
  } catch (e) {
    return { healed: false, reason: `setWebhook failed: ${e && e.message}` };
  }
  if (!set || set.ok !== true) {
    return { healed: false, reason: `setWebhook rejected: ${(set && set.description) || "unknown"}` };
  }
  return { healed: true, reason: sameUrl ? "re-registered (updates or auth drift)" : "registered" };
}

module.exports = { selfHealWebhook, ALLOWED_UPDATES };
