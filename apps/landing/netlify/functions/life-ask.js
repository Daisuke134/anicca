// life-ask.js — Netlify function for B-ask (spec27 WF-B B-ask).
//
// TWO endpoints in one handler (distinguished by `action` query param or body field):
//
//   POST /.netlify/functions/life-ask?action=question   (GCAL-READ-ONLY)
//     gog (the mail-send binary) can't run inside a Netlify lambda, so this
//     action only DETECTS the events that need asking and returns them. The
//     local ask/ask.js (on the Mac-mini) does the actual `gog gmail send` and
//     then calls action=mark-asked to set the pending flag.
//     1. Reads today's GCal events (using gcal-token.js for OAuth2).
//     2. Finds events missing location AND/OR duration (ask-logic.detectMissingInfo).
//     Returns { ok, checked, toAsk: [{ eventId, eventTitle, subject, body }] }.
//
//   POST /.netlify/functions/life-ask?action=mark-asked
//     Called by the local sender (ask/ask.js) after a question email is sent.
//     Body: { eventId, messageId }
//     PATCHes the GCal event with anicca_ask_pending=true to avoid duplicate asks.
//     Returns { ok, eventId }.
//
//   POST /.netlify/functions/life-ask?action=reply
//     Triggered by AgentMail inbound webhook (webhook_id ep_3FBcXGwrcP575GjLm46jCMj2TYr,
//     client_id b-ask-reply-webhook) on message.received for the anicca-life-ask inbox.
//     Body: { message: { id, subject, body, threadId, ... } }
//     1. Ignores non-[Ask] subject messages (returns 200 no-op) so the webhook can safely
//        receive all message.received events without polluting logs.
//     2. Matches the inbound reply to a pending GCal event (via Event ID in the email body).
//     3. Parses location AND/OR duration from the reply body (parseLocationFromReply /
//        parseDurationFromReply). Duration-only replies don't get written as a location.
//     4. PATCHes the GCal event with the resolved location/end + clears pending flag.
//     Returns { ok, eventId, location, durationMinutes }.
//
// Env vars:
//   GOOGLE_CALENDAR_TOKEN or GOOGLE_REFRESH_TOKEN+CLIENT_ID+CLIENT_SECRET (GCal auth)
//   GCAL_ID                          — Google Calendar ID (default: "primary")
//   (Mail SEND is done locally via gog in ask/ask.js — no AgentMail needed here.)

"use strict";

const { getAccessToken } = require("./_lib/gcal-token");
const {
  detectMissingInfo,
  buildQuestionBody,
  buildQuestionSubject,
  buildAskPendingPatch,
  buildResolvePatch,
  parseLocationFromReply,
  parseDurationFromReply,
  DURATION_RE,
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

// ── action=question (GCAL-READ-ONLY) ─────────────────────────────────────────────
// gog can't run on Netlify, so this only DETECTS and returns the events to ask
// (plus the pre-built subject/body). The local ask/ask.js sends the mail via gog,
// then calls action=mark-asked to set the pending flag.

async function handleQuestion(token, calendarId) {
  const events = await listTodayEvents(calendarId, token);
  const missing = detectMissingInfo(events); // [{ event, kind }]
  const toAsk = missing.map(({ event: ev }) => ({
    eventId: ev.id,
    eventTitle: ev.summary || "",
    subject: buildQuestionSubject(ev),
    body: buildQuestionBody(ev),
  }));
  return {
    statusCode: 200,
    body: JSON.stringify({ ok: true, checked: events.length, toAsk }),
  };
}

// ── action=mark-asked handler ────────────────────────────────────────────────────
// Called by the local sender (ask/ask.js) after a question email is sent.
// Body: { eventId, messageId }

async function handleMarkAsked(rawBody, token, calendarId) {
  let p;
  try {
    p = typeof rawBody === "string" ? JSON.parse(rawBody) : rawBody;
  } catch {
    return { statusCode: 400, body: "invalid_json" };
  }
  const { eventId, messageId } = p || {};
  if (!eventId) return { statusCode: 400, body: "missing_event_id" };

  let ev;
  try {
    ev = await getEvent(calendarId, eventId, token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_get_error: ${err.message}` };
  }
  try {
    await patchEvent(calendarId, eventId, buildAskPendingPatch(messageId || "", ev), token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_patch_error: ${err.message}` };
  }
  return { statusCode: 200, body: JSON.stringify({ ok: true, eventId }) };
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

  // Ignore non-[Ask] messages: the AgentMail webhook fires for ALL inbound mail.
  // Return 200 no-op so the webhook endpoint is idempotent for unrelated messages.
  if (!replySubject.includes("[Ask]") && !replyBody.includes("Event ID:")) {
    return { statusCode: 200, body: JSON.stringify({ ok: true, skipped: "not_an_ask_reply" }) };
  }

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

  // Parse location AND/OR duration from reply.
  let location = parseLocationFromReply(replyBody);
  const durationMinutes = parseDurationFromReply(replyBody);
  // Duration-only guard (review point 4): if the only content is a duration
  // like "所要 90分", don't write it as a bogus location.
  if (location && DURATION_RE.test(location)) location = null;
  if (!location && !durationMinutes) {
    return { statusCode: 422, body: "no_location_or_duration_in_reply" };
  }

  // Fetch the current event to build the patch correctly
  let existingEvent;
  try {
    existingEvent = await getEvent(calendarId, eventId, token);
  } catch (err) {
    // 404 = event no longer exists (deleted/cancelled after ask was sent) — not a server error
    if (err.message && err.message.includes("404")) {
      return { statusCode: 404, body: `event_not_found: ${eventId}` };
    }
    return { statusCode: 502, body: `gcal_get_error: ${err.message}` };
  }

  // Patch GCal with the resolved location and/or duration
  const patch = buildResolvePatch({ location, durationMinutes }, existingEvent);
  try {
    await patchEvent(calendarId, eventId, patch, token);
  } catch (err) {
    return { statusCode: 502, body: `gcal_patch_error: ${err.message}` };
  }

  return {
    statusCode: 200,
    body: JSON.stringify({ ok: true, eventId, location, durationMinutes }),
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

  if (action === "mark-asked") {
    return handleMarkAsked(event.body, token, calendarId);
  }

  // Default: action=question (GCal read-only; no mail sent here — the local
  // ask/ask.js does the gog send + mark-asked, since gog can't run on Netlify).
  try {
    return await handleQuestion(token, calendarId);
  } catch (err) {
    return { statusCode: 502, body: `ask_error: ${err.message}` };
  }
};
