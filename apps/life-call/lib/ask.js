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
const { sendMessage: tgSend } = require("./telegram.js");

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

// Raw Gemini generateContent. Key goes in the x-goog-api-key HEADER, never the URL (so it can't leak
// into logs/referrers). Returns the parsed response, or {} on failure.
async function geminiRaw(body, geminiKey) {
  try {
    const r = await fetch(GEMINI, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": geminiKey },
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch { return {}; }
}
// One-shot JSON call (no tools) — for tasks that are a single judgment, not a search.
async function geminiJson(prompt, geminiKey) {
  const j = await geminiRaw({
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { responseMimeType: "application/json", temperature: 0 },
  }, geminiKey);
  try { return JSON.parse(j?.candidates?.[0]?.content?.parts?.[0]?.text || "{}"); } catch { return {}; }
}

// TOOL: Google Places Text Search. The AGENT calls this itself — possibly several times with different
// queries — to find a venue. Returns candidate {name, address}.
// NOTE: this legacy endpoint requires the key as a query param (no header alternative; the v1 API that
// supports header-auth is not enabled on this GCP project). The key is a Maps-restricted browser key,
// not a secret credential, and we never log this URL — see SECURITY note at the call site.
async function placesSearch(query, mapsKey) {
  if (!mapsKey || !query) return [];
  try {
    // No hardcoded language/region — this must work for ANY user worldwide. Places returns each
    // venue's address in its own locale; the agent adds geographic context (the user's home city) to
    // its query itself when it needs to disambiguate.
    const r = await fetch(`https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(query)}&key=${mapsKey}`);
    const j = await r.json();
    return (j.results || []).slice(0, 5).map((p) => ({ name: p.name || "", address: p.formatted_address || "" }));
  } catch { return []; }
}

// The agent's two tools: it searches Places (as many queries as it wants), then submits its verdict.
const RESOLVE_TOOLS = [{
  functionDeclarations: [
    {
      name: "places_search",
      description: "Search Google Places for a real-world venue and get its exact address. Use it (try query variations: bare name, name+area, English/Japanese) to find where an event takes place.",
      parameters: { type: "OBJECT", properties: { query: { type: "STRING", description: "Place name or keywords, e.g. '松竹芸能養成所 東京' or 'JETRO Innovation Garden 赤坂'." } }, required: ["query"] },
    },
    {
      name: "submit_answer",
      description: "Submit your final decision once you've searched enough.",
      parameters: {
        type: "OBJECT",
        properties: {
          confident: { type: "BOOLEAN", description: "true if you found the real venue; false if the title is a person/vague activity and the user must be asked." },
          location: { type: "STRING", description: "The exact formatted_address from a places_search result. Empty when confident=false." },
        },
        required: ["confident"],
      },
    },
  ],
}];

// AGENTIC: the model uses the places_search TOOL itself to find the venue (no spoon-fed candidates),
// then submit_answer. Returns the address, or null (= ask the user). This is the agent doing the
// search a human would do, instead of bothering them.
async function agentResolveLocation(event, { home, mapsKey, geminiKey }) {
  const contents = [{
    role: "user",
    parts: [{ text:
`You are Life Manager. Resolve WHERE this calendar event happens so it can be filled into the user's
calendar WITHOUT bothering them. Use places_search to look it up (more than once if needed). Only when
searching genuinely can't identify a real venue (the title is a person's name, or a vague activity like
"lunch"/"1on1") do you give up — then call submit_answer with confident=false. When you find it, call
submit_answer with confident=true and the exact address from a search result.

Event title: ${JSON.stringify(event.summary || "")}
Start: ${JSON.stringify((event.start || {}).dateTime || "")}
User's home address: ${JSON.stringify(home || "")}` }],
  }];
  for (let turn = 0; turn < 5; turn++) {
    const j = await geminiRaw({ contents, tools: RESOLVE_TOOLS, generationConfig: { temperature: 0 } }, geminiKey);
    const parts = j?.candidates?.[0]?.content?.parts || [];
    const calls = parts.filter((p) => p.functionCall).map((p) => p.functionCall);
    if (!calls.length) return null;
    contents.push({ role: "model", parts });
    const responses = [];
    for (const c of calls) {
      if (c.name === "submit_answer") {
        const a = c.args || {};
        return a.confident && a.location && String(a.location).trim() ? String(a.location).trim() : null;
      }
      if (c.name === "places_search") {
        const res = await placesSearch((c.args || {}).query || "", mapsKey);
        responses.push({ functionResponse: { name: "places_search", response: { results: res } } });
      }
    }
    contents.push({ role: "user", parts: responses });
  }
  return null; // ran out of turns → ask
}

// Reading a reply is a single judgment, not a search — one JSON call (deterministic enough, no tools).
async function agentMatchReply(replyText, pending, geminiKey) {
  if (!pending.length) return null;
  const out = await geminiJson(
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
    // ASK: prefer Telegram when the user linked it (replies come back via the /telegram webhook);
    // otherwise email from their own Gmail via Unipile.
    if (opts.telegramChatId && opts.telegramToken) {
      const r = await tgSend(opts.telegramToken, opts.telegramChatId,
        `📍 Where is “${event.summary || "your event"}”? Just reply here and I’ll add it to your calendar.`);
      if (r && r.ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
    } else if (accountId && unipileToken) {
      const { Subject, Body } = buildAsk(event); // simple, model-free template for the email itself
      const sent = await unipile("POST", "/api/v1/emails", {
        account_id: accountId, to: [{ identifier: userEmail }], subject: Subject, body: Body,
      }, unipileToken, unipileDsn);
      if (sent.ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
    }
  }

  // READ replies (EMAIL users only — Telegram replies arrive via the webhook, not here).
  const pending = events.filter((e) => needsLocation(e) && already.has(e.id));
  if (pending.length && accountId && unipileToken && !opts.telegramChatId) {
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
