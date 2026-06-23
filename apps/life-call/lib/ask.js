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

const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";
const { sendMessage: tgSend } = require("./telegram.js");
const { getCalendar, getMail } = require("./transport/index.js");

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
      description: "Submit your final decision once you've searched (or once you recognize the event needs no place).",
      parameters: {
        type: "OBJECT",
        properties: {
          online: { type: "BOOLEAN", description: "true if this event has NO physical place to travel to — it is online / remote / a phone or video call (e.g. title contains オンライン, 電話, リモート, remote, online, Zoom, Meet, Teams, ビデオ通話, 通話). Then there is NO location to fill and the user must NOT be asked." },
          confident: { type: "BOOLEAN", description: "true ONLY when online=false and you found the real physical venue; false if it is a person/vague activity and the user must be asked." },
          location: { type: "STRING", description: "The exact formatted_address from a places_search result. Empty unless confident=true." },
        },
        required: ["online", "confident"],
      },
    },
  ],
}];

// AGENTIC: the model uses the places_search TOOL itself to find the venue (no spoon-fed candidates),
// then submit_answer. Returns the address, or null (= ask the user). This is the agent doing the
// search a human would do, instead of bothering them.
// Returns { kind: "online" } (no place — never ask, never travel) | { kind: "filled", location }
// (real venue found) | { kind: "ask" } (a human must tell us). The agent classifies online itself —
// "they are LLM agents, they should know" (Dais 2026-06-23): an event like "藤井さんと電話オンライン"
// is online and must never trigger a where-is-it question.
async function agentResolveLocation(event, { home, mapsKey, geminiKey }) {
  const contents = [{
    role: "user",
    parts: [{ text:
`You are Life Manager. For this calendar event, decide WHERE it happens so travel time can be planned —
without bothering the user. Three outcomes via submit_answer:
1. ONLINE: the event has no physical place — it is a phone/video/online/remote call (title has オンライン,
   電話, リモート, remote, online, Zoom, Meet, Teams, ビデオ通話, 通話, or is clearly virtual). Then
   submit_answer(online=true). No location, no question.
2. PHYSICAL & FOUND: it happens at a real venue. Use places_search (try query variations: bare name,
   name+area, English/Japanese, add the user's home city to disambiguate) to find the exact address,
   then submit_answer(online=false, confident=true, location=<exact formatted_address>).
3. UNKNOWN: it is physical but the title is a person's name or a vague activity ("lunch", "1on1") with no
   findable venue — submit_answer(online=false, confident=false). Only then is the user asked.

Event title: ${JSON.stringify(event.summary || "")}
Event location field (may be a room name, a URL, or empty): ${JSON.stringify(event.location || "")}
Start: ${JSON.stringify((event.start || {}).dateTime || "")}
User's home address: ${JSON.stringify(home || "")}` }],
  }];
  for (let turn = 0; turn < 5; turn++) {
    const j = await geminiRaw({ contents, tools: RESOLVE_TOOLS, generationConfig: { temperature: 0 } }, geminiKey);
    const parts = j?.candidates?.[0]?.content?.parts || [];
    const calls = parts.filter((p) => p.functionCall).map((p) => p.functionCall);
    if (!calls.length) return { kind: "ask" };
    contents.push({ role: "model", parts });
    const responses = [];
    for (const c of calls) {
      if (c.name === "submit_answer") {
        const a = c.args || {};
        if (a.online) return { kind: "online" };
        if (a.confident && a.location && String(a.location).trim()) return { kind: "filled", location: String(a.location).trim() };
        return { kind: "ask" };
      }
      if (c.name === "places_search") {
        const res = await placesSearch((c.args || {}).query || "", mapsKey);
        responses.push({ functionResponse: { name: "places_search", response: { results: res } } });
      }
    }
    contents.push({ role: "user", parts: responses });
  }
  return { kind: "ask" }; // ran out of turns → ask
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
  return getCalendar({ apiKey: key }).listEventsRaw(uid, {
    timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(nowMs + 48 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
}
async function patchEvent(uid, eventId, patch, key) {
  return getCalendar({ apiKey: key }).patchEvent(uid, { calendar_id: "primary", event_id: eventId, ...patch });
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
    const res = await agentResolveLocation(event, { home: opts.home, mapsKey, geminiKey });
    if (res.kind === "online") {
      // Online/remote/phone event → no place, no travel, and NEVER ask the user where it is.
      await markAsked(uid, event.id, supaUrl, supaKey); // dedup so it's not reconsidered next tick
      continue;
    }
    if (res.kind === "filled") {
      await patchEvent(uid, event.id, { location: res.location }, composioKey);
      await markAsked(uid, event.id, supaUrl, supaKey);
      autofilled++;
      continue;
    }
    // res.kind === "ask" — a human must tell us.
    // ASK: prefer Telegram when the user linked it (replies come back via the /telegram webhook);
    // otherwise email from their own Gmail via Unipile.
    if (opts.telegramChatId && opts.telegramToken) {
      const r = await tgSend(opts.telegramToken, opts.telegramChatId,
        `📍 Where is “${event.summary || "your event"}”? Just reply here and I’ll add it to your calendar.`);
      if (r && r.ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
    } else if (accountId && unipileToken) {
      const { Subject, Body } = buildAsk(event); // simple, model-free template for the email itself
      const ok = await getMail({ accountId, token: unipileToken, dsn: unipileDsn }).send(userEmail, Subject, Body);
      if (ok) { await markAsked(uid, event.id, supaUrl, supaKey); asked++; }
    }
  }

  // READ replies (EMAIL users only — Telegram replies arrive via the webhook, not here).
  const pending = events.filter((e) => needsLocation(e) && already.has(e.id));
  if (pending.length && accountId && unipileToken && !opts.telegramChatId) {
    const inboxItems = await getMail({ accountId, token: unipileToken, dsn: unipileDsn }).listInbox({ limit: 15 });
    for (const m of inboxItems) {
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
