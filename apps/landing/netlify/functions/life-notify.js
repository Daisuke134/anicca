// life-notify.js — Netlify function for B-notify (spec27 WF-B B-notify).
//
// Two endpoints (discriminated by X-Anicca-Event header):
//
//   POST /life-notify  (no special header)
//     → "scan" mode: called by heartbeat.
//       1. Fetch today's GCal events.
//       2. detectLateRiskEvents — find events with a started [Travel] block.
//       3. For each at-risk event:
//          a. Build draft body (buildAttendeeDraft).
//          b. Save draft to AgentMail Drafts (durable hold).
//          c. Send approval email to owner via AgentMail (buildApprovalEmail).
//       Returns { ok, scanned, alerted }.
//
//   POST /life-notify  (X-Anicca-Event: message.received)
//     → "webhook" mode: called by AgentMail when owner replies.
//       1. Parse body: { threadId, draftId, replyBody }.
//       2. extractApproval — check if owner said "OK".
//       3. If approved → fetch draft from AgentMail → send to attendee emails.
//       Returns { ok, sent, approved }.
//
// Auth: same GCal OAuth pattern as life-travel.js.
// AgentMail API: https://docs.agentmail.to (inbox: AGENTMAIL_INBOX_ID).
//
// Pattern mirrors life-travel.js (proven WF-B template).

const { getAccessToken } = require("./_lib/gcal-token");
const {
  detectLateRiskEvents,
  estimateMinutesLate,
  buildAttendeeDraft,
  buildApprovalEmail,
  extractApproval,
} = require("./_lib/notify-logic");

// ── GCal REST helper ──────────────────────────────────────────────────────────

/**
 * Fetch today's events from Google Calendar.
 */
async function listTodayEvents(calendarId, token) {
  const now = new Date();
  const timeMin = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const timeMax = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();

  const url =
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events` +
    `?timeMin=${encodeURIComponent(timeMin)}&timeMax=${encodeURIComponent(timeMax)}` +
    `&singleEvents=true&orderBy=startTime&maxResults=50`;

  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) throw new Error(`GCal list ${r.status}: ${await r.text()}`);
  const body = await r.json();
  return body.items || [];
}

// ── AgentMail helpers ─────────────────────────────────────────────────────────

/**
 * Save a message as a Draft in AgentMail.
 * Returns the draft object { id, ... }.
 */
async function saveAgentMailDraft({ inboxId, apiKey, to, subject, body }) {
  const url = `https://api.agentmail.to/v0/inboxes/${encodeURIComponent(inboxId)}/drafts`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ to, subject, body }),
  });
  if (!r.ok) throw new Error(`AgentMail draft ${r.status}: ${await r.text()}`);
  return r.json();
}

/**
 * Send an email directly via AgentMail (not a draft).
 */
async function sendAgentMailEmail({ inboxId, apiKey, to, subject, body }) {
  const url = `https://api.agentmail.to/v0/inboxes/${encodeURIComponent(inboxId)}/messages/send`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ to, subject, body }),
  });
  if (!r.ok) throw new Error(`AgentMail send ${r.status}: ${await r.text()}`);
  return r.json();
}

/**
 * Fetch a draft by ID from AgentMail.
 */
async function getAgentMailDraft({ inboxId, apiKey, draftId }) {
  const url = `https://api.agentmail.to/v0/inboxes/${encodeURIComponent(inboxId)}/drafts/${encodeURIComponent(draftId)}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!r.ok) throw new Error(`AgentMail get-draft ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── Handler ───────────────────────────────────────────────────────────────────

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "method not allowed" };
  }

  const agentMailInboxId = process.env.AGENTMAIL_INBOX_ID;
  const agentMailApiKey  = process.env.AGENTMAIL_API_KEY;
  const ownerEmail       = process.env.OWNER_EMAIL;
  const calendarId       = process.env.GCAL_ID || "primary";

  if (!agentMailInboxId || !agentMailApiKey || !ownerEmail) {
    return { statusCode: 500, body: "missing_env: AGENTMAIL_INBOX_ID, AGENTMAIL_API_KEY, OWNER_EMAIL required" };
  }

  // ── Webhook mode: owner replied "OK" ─────────────────────────────────────
  const isWebhook = (event.headers["x-anicca-event"] || "").toLowerCase() === "message.received";

  if (isWebhook) {
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch {
      return { statusCode: 400, body: "bad_json" };
    }

    const { draftId, replyBody } = body;
    if (!draftId || typeof replyBody !== "string") {
      return { statusCode: 400, body: "missing_fields: draftId, replyBody required" };
    }

    const approved = extractApproval(replyBody);
    if (!approved) {
      return { statusCode: 200, body: JSON.stringify({ ok: true, approved: false, sent: 0 }) };
    }

    // Fetch the saved draft and send it to attendees
    let draft;
    try {
      draft = await getAgentMailDraft({ inboxId: agentMailInboxId, apiKey: agentMailApiKey, draftId });
    } catch (err) {
      return { statusCode: 502, body: `draft_fetch_error: ${err.message}` };
    }

    // draft.to is the attendee email list (set when draft was created)
    const attendeeEmails = Array.isArray(draft.to) ? draft.to : [draft.to].filter(Boolean);
    let sentCount = 0;
    for (const to of attendeeEmails) {
      try {
        await sendAgentMailEmail({
          inboxId: agentMailInboxId,
          apiKey: agentMailApiKey,
          to,
          subject: draft.subject || "Update from Anicca",
          body: draft.body || "",
        });
        sentCount += 1;
      } catch {
        // Log and continue — partial success acceptable
      }
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true, approved: true, sent: sentCount }),
    };
  }

  // ── Scan mode: heartbeat trigger ──────────────────────────────────────────

  let gcalToken;
  try {
    gcalToken = await getAccessToken();
  } catch (err) {
    return { statusCode: 500, body: `auth_error: ${err.message}` };
  }

  let events;
  try {
    events = await listTodayEvents(calendarId, gcalToken);
  } catch (err) {
    return { statusCode: 502, body: `gcal_list_error: ${err.message}` };
  }

  const nowMs = Date.now();
  const risks = detectLateRiskEvents(events, nowMs);
  const alerted = [];

  for (const { event: ev, travelEvent } of risks) {
    const travelStartMs = new Date(travelEvent.start.dateTime).getTime();
    const minutesLate = estimateMinutesLate({ travelStartMs, nowMs });
    const attendees = ev.attendees || [];

    const draftBody = buildAttendeeDraft({
      eventSummary: ev.summary,
      minutesLate,
    });

    // Build attendee email addresses list (to field for the draft)
    const attendeeEmails = attendees.map((a) => a.email).filter(Boolean);
    const draftTo = attendeeEmails.length > 0 ? attendeeEmails.join(",") : ownerEmail;

    // Save draft to AgentMail Drafts
    let draft;
    try {
      draft = await saveAgentMailDraft({
        inboxId: agentMailInboxId,
        apiKey: agentMailApiKey,
        to: draftTo,
        subject: `Late notice for "${ev.summary}"`,
        body: draftBody,
      });
    } catch (err) {
      alerted.push({ error: `draft_save: ${err.message}`, event: ev.summary });
      continue;
    }

    // Send approval email to owner
    const approvalEmail = buildApprovalEmail({
      ownerEmail,
      eventSummary: ev.summary,
      attendees,
      draftBody,
      draftId: draft.id,
    });

    try {
      await sendAgentMailEmail({
        inboxId: agentMailInboxId,
        apiKey: agentMailApiKey,
        to: approvalEmail.to,
        subject: approvalEmail.subject,
        body: approvalEmail.body,
      });
      alerted.push({ event: ev.summary, draftId: draft.id, minutesLate });
    } catch (err) {
      alerted.push({ error: `approval_send: ${err.message}`, event: ev.summary });
    }
  }

  return {
    statusCode: 200,
    body: JSON.stringify({
      ok: true,
      scanned: events.length,
      lateRisks: risks.length,
      alerted,
    }),
  };
};
