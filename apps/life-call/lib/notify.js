// lib/notify.js — cloud late-notice. The user tells the bot they're running late; the agent finds the
// right event + its external attendee, drafts a short apology, and sends it from OUR domain via Resend
// "on behalf of" the user, with Reply-To = the user's email so attendees reach the human. We never read
// or send from the user's Gmail. No location, no auto-guessing — the user initiates, the agent does the work.
"use strict";

const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";
const { getCalendar } = require("./transport/index.js");
const { resendSend } = require("./mail-resend.js");

async function geminiJson(prompt, geminiKey) {
  try {
    const r = await fetch(`${GEMINI}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": geminiKey },
      body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { responseMimeType: "application/json", temperature: 0 } }),
    });
    const j = await r.json();
    return JSON.parse(j?.candidates?.[0]?.content?.parts?.[0]?.text || "{}");
  } catch { return {}; }
}

// Is this message the user saying they're running late? Returns { isLate, etaMinutes }.
async function classifyLate(text, geminiKey) {
  const out = await geminiJson(
    `Does this message mean the user is running LATE to a meeting/event (or wants someone told they're late)?
Message: ${JSON.stringify((text || "").slice(0, 500))}
Reply JSON: {"isLate": true|false, "etaMinutes": <integer minutes late, or null if not stated>}.`,
    geminiKey,
  );
  return { isLate: out.isLate === true, etaMinutes: Number.isFinite(out.etaMinutes) ? out.etaMinutes : null };
}

// The user said they're late. Find the event they mean + its external attendee, draft + send the notice.
// Returns { sent, to, event, etaMinutes } — sent:false when there's nothing to notify.
async function sendLateNotice(uid, text, opts) {
  const { composioKey, geminiKey, resendKey, userEmail, userName } = opts;
  const nowMs = opts.nowMs || Date.now();
  if (!composioKey || !geminiKey || !resendKey) return { sent: false };

  // Events from a bit before now to +6h that have at least one EXTERNAL attendee (someone to notify).
  const items = await getCalendar({ apiKey: composioKey, gmailAccountId: opts.gmailAccountId }).listEventsRaw(uid, {
    timeMin: new Date(nowMs - 30 * 60000).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(nowMs + 6 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
    maxResults: 25,
  });
  const events = items
    .map((e) => ({ id: e.id, summary: e.summary || "", start: (e.start || {}).dateTime || "",
      attendees: (e.attendees || []).filter((a) => a && a.email && !a.self && !a.organizer).map((a) => a.email) }))
    .filter((e) => e.attendees.length);
  if (!events.length) return { sent: false };

  // Let the model pick which event the user means + the attendee + the ETA from the message.
  const pick = await geminiJson(
    `The user is running late and sent: ${JSON.stringify((text || "").slice(0, 500))}.
Pick which event they mean and who to notify, from this list (now is ${new Date(nowMs).toISOString()}):
${JSON.stringify(events)}
Reply JSON: {"eventId":"<id>"|null, "to":"<one attendee email from that event>"|null, "etaMinutes":<int|null>}.`,
    geminiKey,
  );
  const ev = events.find((e) => e.id === pick.eventId);
  const to = ev && ev.attendees.includes(pick.to) ? pick.to : (ev ? ev.attendees[0] : null);
  if (!ev || !to) return { sent: false };

  const eta = Number.isFinite(pick.etaMinutes) ? pick.etaMinutes : (opts.etaMinutes || null);
  const who = userName || "I";
  const subject = `Running late — ${ev.summary || "our meeting"}`;
  const body = `Hi,\n\n${who === "I" ? "I'm" : who + " is"} running ${eta ? `about ${eta} minutes ` : ""}late to ${ev.summary || "our meeting"}. ` +
    `Apologies for the delay — ${who === "I" ? "I'll" : "they'll"} be there as soon as possible.\n\nThanks for your patience.`;
  // Send from our domain on the user's behalf; Reply-To = the user's email so the attendee can reach them.
  const signed = `${body}\n\n— Sent by Life Manager on behalf of ${userName || "your contact"}.`;
  const r = await resendSend({ to, subject, text: signed, replyTo: userEmail, resendKey });
  return { sent: !!(r && r.sent), to, event: ev.summary, etaMinutes: eta };
}

module.exports = { classifyLate, sendLateNotice };
