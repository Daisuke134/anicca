// life-ask.js — Netlify function for B-ask (spec27 WF-B B-ask).
//
// TWO endpoints in one handler (distinguished by `action` query param or body field):
//
//   POST /.netlify/functions/life-ask?action=question
//     Triggered by Anicca's heartbeat (schedule-derived trigger, spec27 §2 patch).
//     1. Reads today's GCal events (using gcal-token.js for OAuth2).
//     2. Finds events with no `location` field (via ask-logic.detectMissingLocations).
//     3. Sends a question email to Dais via AgentMail for each missing location.
//     4. Patches the GCal event with anicca_ask_pending=true to avoid duplicate asks.
//     Returns { ok, asked: [{ eventId, eventTitle, messageId }] }.
//
//   POST /.netlify/functions/life-ask?action=reply
//     Triggered by AgentMail inbound webhook (message.received event).
//     Body: { message: { id, subject, body, threadId, ... } }
//     1. Matches the inbound reply to a pending GCal event (via Event ID in the email body).
//     2. Parses the location from the reply body (via ask-logic.parseLocationFromReply).
//     3. PATCHes the GCal event with the resolved location + clears pending flag.
//     Returns { ok, eventId, location }.
//
// Pattern mirrors life-travel.js (proven template).
// Auth: GOOGLE_CALENDAR_TOKEN or GOOGLE_REFRESH_TOKEN+CLIENT_ID+CLIENT_SECRET
// AgentMail: AGENTMAIL_API_KEY + AGENTMAIL_INBOX_ID + DAIS_EMAIL

"use strict";

const { getAccessToken } = require("./_lib/gcal-token");
const {
  detectMissingLocations,
  buildQuestionBody,
  buildQuestionSubject,
  buildAskPendingPatch,
  buildLocationPatch,
  parseLocationFromReply,
} = require("./_lib/ask-logic");

// ── GCal REST helpers ──────────────────────────────────────────────────────────

async function listTodayEvents(calendarId, token) {
  const now = new Date();
  const timeMin = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const timeMax = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();

  const url =
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events` +
    `?timeMin=${encodeURIComponent(timeMin)}&timeMax=${encodeURIComponent(timeMax)}` +
    `&singleEvents=true&orderBy=startTime&maxResults=50`;

  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`GCal list ${r.status}: ${await r.text()}`);
  const body = await r.json();
  return body.items || [];
}

async function patchEvent(calendarId, eventId, patchBody, token) {
  const url =
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`;
  const r = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patchBody),
  });
  if (!r.ok) throw new Error(`GCal patch ${r.status}: ${await r.text()}`);
  return r.json();
}

async function getEvent(calendarId, eventId, token) {
  const url =
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`GCal get ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── AgentMail REST helper ──────────────────────────────────────────────────────

async function sendEmail({ apiKey, inboxId, to, subject, text }) {
  // Correct endpoint: /messages/send (not /messages which is list-only)
  const url = `https://api.agentmail.to/v0/inboxes/${encodeURIComponent(inboxId)}/messages/send`;
  // AgentMail v0 "to" field accepts array of strings (email addresses)
  const toArray = Array.isArray(to) ? to : [to];
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ to: toArray, subject, text }),
  });
  if (!r.ok) throw new Error(`AgentMail send ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── action=question handler ────────────────────────────────────────────────────

async function handleQuestion(token, calendarId, agentMailCfg) {
  const events = await listTodayEvents(calendarId, token);
  const missing = detectMissingLocations(events);
  const asked = [];

  for (const ev of missing) {
    const subject = buildQuestionSubject(ev);
    const text = buildQuestionBody(ev);

    let messageId = "";
    try {
      const sent = await sendEmail({
        apiKey: agentMailCfg.apiKey,
        inboxId: agentMailCfg.inboxId,
        to: agentMailCfg.daisEmail,
        subject,
        text,
      });
      messageId = sent?.id || sent?.messageId || "";
    } catch (err) {
      // Log and continue — partial success is better than hard failure
      asked.push({ eventId: ev.id, eventTitle: ev.summary, error: err.message });
      continue;
    }

    // Patch GCal event to mark ask as pending
    const pendingPatch = buildAskPendingPatch(messageId, ev);
    try {
      await patchEvent(calendarId, ev.id, pendingPatch, token);
    } catch (err) {
      // Non-fatal: email was sent, patch failed — log but don't abort
      asked.push({ eventId: ev.id, eventTitle: ev.summary, messageId, patchError: err.message });
      continue;
    }

    asked.push({ eventId: ev.id, eventTitle: ev.summary, messageId });
  }

  return {
    statusCode: 200,
    body: JSON.stringify({ ok: true, checked: events.length, asked }),
  };
}

// ── action=reply handler ───────────────────────────────────────────────────────

async function handleReply(body, token, calendarId) {
  // AgentMail webhook payload: { message: { id, subject, body, ... } }
  let parsed;
  try {
    parsed = typeof body === "string" ? JSON.parse(body) : body;
  } catch {
    return { statusCode: 400, body: "invalid_json" };
  }

  const message = parsed?.message || parsed;
  const replyBody = message?.body || message?.text || "";
  const replySubject = message?.subject || "";

  // Extract Event ID from the reply body (embedded by buildQuestionBody)
  const eventIdMatch = replyBody.match(/Event ID:\s*([^\s\r\n]+)/);
  if (!eventIdMatch) {
    // Try to match from subject line as fallback (not expected but defensive)
    return { statusCode: 400, body: "no_event_id_in_reply" };
  }
  const eventId = eventIdMatch[1].trim();

  if (!eventId || eventId === "unknown") {
    return { statusCode: 400, body: "invalid_event_id" };
  }

  // Parse location from reply
  const location = parseLocationFromReply(replyBody);
  if (!location) {
    return { statusCode: 422, body: "no_location_found_in_reply" };
  }

  // Fetch the current event to build the patch correctly
  let existingEvent;
  try {
    existingEvent = await getEvent(calendarId, eventId, token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_get_error: ${err.message}` };
  }

  // Patch GCal with the resolved location
  const patch = buildLocationPatch(location, existingEvent);
  try {
    await patchEvent(calendarId, eventId, patch, token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_patch_error: ${err.message}` };
  }

  return {
    statusCode: 200,
    body: JSON.stringify({ ok: true, eventId, location }),
  };
}

// ── Main handler ───────────────────────────────────────────────────────────────

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "method not allowed" };
  }

  const action =
    event.queryStringParameters?.action ||
    (() => {
      try {
        return JSON.parse(event.body || "{}")?.action;
      } catch {
        return undefined;
      }
    })() ||
    "question";

  // Auth
  let token;
  try {
    token = await getAccessToken();
  } catch (err) {
    return { statusCode: 500, body: `auth_error: ${err.message}` };
  }

  const calendarId = process.env.GCAL_ID || "primary";

  if (action === "reply") {
    return handleReply(event.body, token, calendarId);
  }

  // Default: action=question
  const apiKey = process.env.AGENTMAIL_API_KEY;
  const inboxId = process.env.AGENTMAIL_INBOX_ID;
  const daisEmail = process.env.DAIS_EMAIL || "keiodaisuke@gmail.com";

  if (!apiKey || !inboxId) {
    return { statusCode: 500, body: "missing AGENTMAIL_API_KEY or AGENTMAIL_INBOX_ID" };
  }

  try {
    return await handleQuestion(token, calendarId, { apiKey, inboxId, daisEmail });
  } catch (err) {
    return { statusCode: 502, body: `ask_error: ${err.message}` };
  }
};
