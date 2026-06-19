// lib/ask.js — cloud ask/reply loop. For events missing a location, email the user (FROM their own
// Gmail, via Unipile) "where is this?", then read their reply (Unipile inbox) and write the location
// onto the event (Composio gcal). The "ask, read the reply, register" loop, omni-channel-ready.
//
//   SEND phase: list next-48h events, detect those missing a location and not already pending,
//     send the question (Event ID embedded), mark the event anicca_ask_pending so we don't re-ask.
//   READ phase: scan the last 2 days of inbox, match replies by "Event ID: <id>", parse the location,
//     PATCH the event location, clear the pending flag.
"use strict";

const {
  detectMissingInfo, buildQuestionBody, buildQuestionSubject, parseLocationFromReply,
} = require("./ask-logic.js");

const COMPOSIO = "https://backend.composio.dev/api/v3";

async function composio(tool, args, key) {
  const r = await fetch(`${COMPOSIO}/tools/execute/${tool}`, {
    method: "POST", headers: { "x-api-key": key, "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: args.user_id, arguments: args.arguments }),
  });
  return r.json().catch(() => ({}));
}

async function unipile(method, path, body, token, dsn) {
  const r = await fetch(`https://${dsn}${path}`, {
    method, headers: { "X-API-KEY": token, "Content-Type": "application/json", accept: "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { ok: r.ok, json: await r.json().catch(() => ({})) };
}

async function listEvents48h(uid, key, nowMs) {
  const j = await composio("GOOGLECALENDAR_EVENTS_LIST", {
    user_id: uid, arguments: {
      calendarId: "primary", singleEvents: true, orderBy: "startTime",
      timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
      timeMax: new Date(nowMs + 48 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
    },
  }, key);
  return ((j.data || {}).items) || [];
}

async function patchEvent(uid, eventId, patch, key) {
  return composio("GOOGLECALENDAR_PATCH_EVENT", {
    user_id: uid, arguments: { calendar_id: "primary", event_id: eventId, ...patch },
  }, key);
}

// Dedup via Supabase lm_ask_log (GOOGLECALENDAR_PATCH_EVENT can't set extendedProperties, so we
// can't flag the event itself). One row per (uid, event_id) we've asked about.
async function askedSet(uid, supaUrl, supaKey) {
  const r = await fetch(`${supaUrl}/rest/v1/lm_ask_log?uid=eq.${encodeURIComponent(uid)}&select=event_id`,
    { headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` } });
  const d = await r.json().catch(() => []);
  return new Set((Array.isArray(d) ? d : []).map((x) => x.event_id));
}
async function markAsked(uid, eventId, supaUrl, supaKey) {
  await fetch(`${supaUrl}/rest/v1/lm_ask_log`, {
    method: "POST",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ uid, event_id: eventId }),
  }).catch(() => {});
}

// Returns { asked, resolved }.
async function askTick(uid, opts) {
  const { composioKey, accountId, unipileToken, unipileDsn, userEmail, supaUrl, supaKey } = opts;
  const nowMs = opts.nowMs || Date.now();
  let asked = 0, resolved = 0;
  const events = await listEvents48h(uid, composioKey, nowMs);
  const already = await askedSet(uid, supaUrl, supaKey);

  // SEND: events missing location we haven't already asked about.
  const missing = detectMissingInfo(events).filter((m) => m.kind.location && !already.has(m.event.id));
  for (const { event } of missing) {
    const sent = await unipile("POST", "/api/v1/emails", {
      account_id: accountId, to: [{ identifier: userEmail }],
      subject: buildQuestionSubject(event), body: buildQuestionBody(event), // body embeds "Event ID: <id>"
    }, unipileToken, unipileDsn);
    if (sent.ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
  }

  // READ: scan recent inbox for replies carrying an Event ID + a location → write location to the event.
  const inbox = await unipile("GET", `/api/v1/emails?account_id=${encodeURIComponent(accountId)}&limit=20`, null, unipileToken, unipileDsn);
  for (const m of (inbox.json.items) || []) {
    const text = m.body_plain || m.body || m.snippet || "";
    const idMatch = text.match(/Event ID:\s*([^\s\r\n]+)/);
    if (!idMatch) continue;
    const eventId = idMatch[1].trim();
    if (!eventId || eventId === "unknown" || !already.has(eventId)) continue; // only events we asked
    const location = parseLocationFromReply(text);
    if (!location) continue;
    const ev = events.find((e) => e.id === eventId);
    if (!ev || (ev.location || "").trim()) continue; // already has a location
    await patchEvent(uid, eventId, { location }, composioKey); // PATCH accepts location
    resolved++;
  }
  return { asked, resolved };
}

module.exports = { askTick };
