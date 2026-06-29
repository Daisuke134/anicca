"use strict";
// Own-domain email for the WEB ask/reply loop. We NEVER read the user's Gmail — we SEND from our own
// verified domain via Resend, and route replies back via a short opaque token in the Reply-To local-part
// (reply+<token>@reply.aniccaai.com → Cloudflare Email Routing → POST /inbound-email, which looks the token
// up in lm_ask_log). Flat cost, no per-user fee, no Google restricted-scope CASA. The CALLER generates the
// token (newReplyToken) and stores token→(uid,eventId) before sending. Telegram users don't use this at all.
const FROM = process.env.LM_MAIL_FROM || "Life Manager <hello@aniccaai.com>";
const REPLY_DOMAIN = process.env.LM_REPLY_DOMAIN || "reply.aniccaai.com";
const RESEND_URL = "https://api.resend.com/emails";

// reply+<token>@reply.aniccaai.com — the catch-all inbound address. Local part = 6 + 22 = 28 chars (< 64).
function replyToFor(token) {
  return `reply+${token}@${REPLY_DOMAIN}`;
}

// Low-level Resend send. Fail-closed (no key / no recipient → {sent:false}), never throws.
async function resendSend({ to, subject, text, replyTo, resendKey, fetchImpl }) {
  if (!resendKey) return { sent: false, error: "no RESEND_API_KEY" };
  if (!to || (Array.isArray(to) && to.length === 0) || !subject) return { sent: false, error: "missing to/subject" };
  const f = fetchImpl || fetch;
  try {
    const r = await f(RESEND_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${resendKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from: FROM, to: Array.isArray(to) ? to : [to], subject, text, reply_to: replyTo }),
    });
    const d = await r.json().catch(() => ({}));
    return { sent: !!r.ok, id: d.id, status: r.status, error: r.ok ? undefined : (d.message || `http ${r.status}`) };
  } catch (e) {
    return { sent: false, error: String(e) };
  }
}

// Ask the USER where an event is. Reply-To carries the signed token → their reply hits /inbound-email,
// which parses the token, matches the event, and patches the calendar.
async function sendAsk({ to, replyToken, event, resendKey, fetchImpl }) {
  const name = (event && event.summary) || "your event";
  const subject = `Where is “${name}”?`;
  const text =
    `Hi — I'm setting up travel time for “${name}”, but I can't find where it is.\n\n` +
    `Just reply to this email with the address or place name, and I'll add it to your calendar and call you in time.\n\n— Life Manager`;
  return resendSend({ to, subject, text, replyTo: replyToFor(replyToken), resendKey, fetchImpl });
}

// Tell the ATTENDEES the user is running late. Sent from our domain "on behalf of <userName>"; Reply-To is
// the user's REAL email so attendee replies reach the human directly.
async function sendLateNotice({ toAttendees, userName, event, etaMinutes, userEmail, resendKey, fetchImpl }) {
  const name = (event && event.summary) || "the meeting";
  const who = userName || "Your contact";
  const subject = `Running late: ${name}`;
  const eta = Number.isFinite(etaMinutes) ? `about ${etaMinutes} minutes` : "a little";
  const text =
    `Hi — ${who} is running ${eta} late to “${name}” and wanted you to know.\n\n` +
    `(Sent automatically by Life Manager on ${who}'s behalf — reply to reach ${who} directly.)`;
  return resendSend({ to: toAttendees, subject, text, replyTo: userEmail, resendKey, fetchImpl });
}

module.exports = { sendAsk, sendLateNotice, resendSend, replyToFor, FROM, REPLY_DOMAIN };
