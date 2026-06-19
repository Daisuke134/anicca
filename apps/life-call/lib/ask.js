// lib/ask.js — AGENTIC ask/reply loop for event locations. NO regex heuristics, NO string-match
// confidence — an LLM (Gemini) reasons about everything (decision #47: agentic, not hardcoded):
//
//   RESOLVE  : for each event missing a location, Gemini decides the real place + address (grounded
//              on a Google Places search so it can't hallucinate a street number), or says "ask".
//   ASK      : only when Gemini can't determine it (e.g. "Coffee with Mai" — a person, no venue) do
//              we email the user (via Unipile, from their own Gmail).
//   READ     : Gemini reads inbound replies + the list of pending events and returns {eventId,
//              location} — no regex parsing of quoted threads.
//
// Dedup is the one deterministic part (a Supabase lm_ask_log row per asked event) — that's bookkeeping,
// not judgment.
"use strict";

const COMPOSIO = "https://backend.composio.dev/api/v3";
const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";

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

// One Gemini JSON call. Returns the parsed object, or {} on any failure (caller treats as "unsure").
async function gemini(prompt, geminiKey) {
  try {
    const r = await fetch(`${GEMINI}?key=${geminiKey}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { responseMimeType: "application/json", temperature: 0 },
      }),
    });
    const j = await r.json();
    const text = j?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
    return JSON.parse(text);
  } catch { return {}; }
}

// Grounding: real candidate places for a title (so the model picks a real address, never invents one).
async function placesCandidates(title, mapsKey) {
  if (!mapsKey || !title) return [];
  try {
    const r = await fetch(`https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(title)}&language=ja&key=${mapsKey}`);
    const j = await r.json();
    return (j.results || []).slice(0, 4).map((p) => ({ name: p.name, address: p.formatted_address }));
  } catch { return []; }
}

// AGENTIC: decide the address for an event, or null (= ask the user).
async function agentResolveLocation(event, { home, mapsKey, geminiKey }) {
  const candidates = await placesCandidates(event.summary || "", mapsKey);
  const out = await gemini(
    `You resolve the real-world location of a personal calendar event. Decide ONLY if you are confident.
Event title: ${JSON.stringify(event.summary || "")}
Start: ${JSON.stringify((event.start || {}).dateTime || "")}
User's home address: ${JSON.stringify(home || "")}
Real place candidates from Google Places (use ONLY these for the address — never invent one):
${JSON.stringify(candidates)}

If the title clearly names a real venue/place that matches one candidate (e.g. a school, office, shop,
station, restaurant), return that candidate's address. If the title is a person, a vague activity, or
you cannot confidently match a candidate, return null (we'll ask the user).
Reply as JSON: {"location": "<exact candidate address>" | null}`,
    geminiKey,
  );
  return typeof out.location === "string" && out.location.trim() ? out.location.trim() : null;
}

// AGENTIC: read a reply against the pending events; return {eventId, location} or null.
async function agentMatchReply(replyText, pending, geminiKey) {
  if (!pending.length) return null;
  const out = await gemini(
    `A user replied to an email asking where one of their events takes place. Match the reply to the
correct event and extract the location they gave. Ignore quoted/original text.
Pending events (id → title):
${JSON.stringify(pending.map((p) => ({ id: p.id, title: p.summary })))}
Reply text:
${JSON.stringify((replyText || "").slice(0, 2000))}

Reply as JSON: {"eventId": "<id from the list>" | null, "location": "<place/address they gave>" | null}.
Use null for both if the reply doesn't clearly answer a location question.`,
    geminiKey,
  );
  if (out && out.eventId && out.location) return { eventId: String(out.eventId), location: String(out.location) };
  return null;
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
function needsLocation(ev) {
  const s = (ev.summary || "").trim();
  if (s.startsWith("[Travel]") || s.startsWith("[Ask]")) return false;
  if (!((ev.start || {}).dateTime)) return false;
  return !((ev.location || "").trim());
}

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

// Returns { autofilled, asked, resolved }.
async function askTick(uid, opts) {
  const { composioKey, accountId, unipileToken, unipileDsn, userEmail, supaUrl, supaKey, mapsKey, geminiKey } = opts;
  const nowMs = opts.nowMs || Date.now();
  let autofilled = 0, asked = 0, resolved = 0;
  const events = await listEvents48h(uid, composioKey, nowMs);
  const already = await askedSet(uid, supaUrl, supaKey);

  // For each event missing a location we haven't handled: agentic resolve, then ask only if unsure.
  for (const event of events.filter((e) => needsLocation(e) && !already.has(e.id))) {
    const found = await agentResolveLocation(event, { home: opts.home, mapsKey, geminiKey });
    if (found) {
      await patchEvent(uid, event.id, { location: found }, composioKey);
      await markAsked(uid, event.id, supaUrl, supaKey);
      autofilled++;
      continue;
    }
    const { Subject, Body } = buildAsk(event); // simple, model-free template for the email itself
    const sent = await unipile("POST", "/api/v1/emails", {
      account_id: accountId, to: [{ identifier: userEmail }], subject: Subject, body: Body,
    }, unipileToken, unipileDsn);
    if (sent.ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
  }

  // READ replies: agentically match each reply to a pending event + extract the location.
  const pending = events.filter((e) => needsLocation(e) && already.has(e.id));
  if (pending.length) {
    const inbox = await unipile("GET", `/api/v1/emails?account_id=${encodeURIComponent(accountId)}&limit=15`, null, unipileToken, unipileDsn);
    for (const m of (inbox.json.items) || []) {
      if (!/^Re:/i.test(m.subject || "")) continue;
      const text = m.body_plain || m.body || m.snippet || "";
      const match = await agentMatchReply(text, pending, geminiKey);
      if (!match) continue;
      const ev = pending.find((e) => e.id === match.eventId);
      if (!ev) continue;
      await patchEvent(uid, ev.id, { location: match.location }, composioKey);
      resolved++;
    }
  }
  return { autofilled, asked, resolved };
}

// The ask EMAIL is a fixed template (no judgment needed — just a courteous prompt). The Event title +
// id go in so a human reply is natural; the model does the reading on the way back.
function buildAsk(event) {
  const title = event.summary || "your event";
  return {
    Subject: `[Ask] 場所を教えて — ${title}`,
    Body: `Anicca より確認です。\n\n予定「${title}」の場所がまだ設定されていません。どこで行われますか？ この메일にそのまま返信してください（店名・住所どちらでもOK）。Anicca がカレンダーに反映します。\n\n--- Event ID: ${event.id || "unknown"}`,
  };
}

module.exports = { askTick, agentResolveLocation, agentMatchReply };
