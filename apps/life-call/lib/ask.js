// lib/ask.js — AGENTIC ask/reply loop for event locations. NO regex heuristics, NO string-match
// confidence — an LLM (Gemini) reasons about everything (decision #47: agentic, not hardcoded):
//
//   RESOLVE  : for each event missing a location, Gemini decides the real place + address (grounded
//              on a Google Places search so it can't hallucinate a street number), or says "ask".
//   ASK      : only when Gemini can't determine it (e.g. "Coffee with Mai" — a person, no venue) do we
//              ask — via Telegram if linked, else an email from OUR domain (Resend, From hello@aniccaai.com,
//              Reply-To reply+<token>@reply.aniccaai.com). We NEVER read or send from the user's Gmail.
//   READ     : replies arrive on webhooks (Telegram → /telegram, email → /inbound-email). Gemini reads the
//              reply text + the pending event and returns {eventId, location} — no inbox polling, no regex.
//
// Dedup is the one deterministic part (a Supabase lm_ask_log row per asked event) — that's bookkeeping,
// not judgment.
"use strict";

const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";
const { sendMessage: tgSend } = require("./telegram.js");
const { getCalendar, getMail } = require("./transport/index.js");
const { placeKey, recallPlace, rememberPlace } = require("./places-memory.js");
const { newReplyToken } = require("./reply-token.js");
const { sendAsk } = require("./mail-resend.js");

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

function responseText(j) {
  return (j?.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").filter(Boolean).join("\n");
}

function responseFunctionArgs(j, name) {
  const parts = j?.candidates?.[0]?.content?.parts || [];
  const call = parts.map((p) => p.functionCall).find((f) => f && f.name === name);
  return (call && call.args) || {};
}

async function agentSearchCandidate(event, deps = {}) {
  const raw = deps.geminiRaw || geminiRaw;
  const empty = { found: false, candidate: "", source: "" };
  if (!deps.geminiKey && !deps.geminiRaw) return empty;
  let snippets = [];
  const mail = deps.mail || getMail({
    accountId: deps.gmailAccountId, token: deps.unipileToken, dsn: deps.unipileDsn,
  });
  if (mail && typeof mail.searchInbox === "function" && (!mail.ready || mail.ready())) {
    snippets = await mail.searchInbox(String(event.summary || "")).catch(() => []);
  }
  const compactMail = snippets.slice(0, 5).map((m) => ({
    subject: m.subject || "", body: String(m.body || m.text || m.snippet || "").slice(0, 1000),
  }));
  const grounded = await raw({
    contents: [{ role: "user", parts: [{ text:
      `Find the physical venue for this calendar event. Use Google Search and the optional Gmail snippets as evidence. Do not guess.\nEvent title: ${JSON.stringify(event.summary || "")}\nDescription: ${JSON.stringify(event.description || "")}\nGmail snippets: ${JSON.stringify(compactMail)}` }] }],
    tools: [{ google_search: {} }],
    generationConfig: { temperature: 0 },
  }, deps.geminiKey);
  const groundedText = responseText(grounded);
  if (!groundedText) return empty;
  const extracted = await raw({
    contents: [{ role: "user", parts: [{ text:
      `Extract a venue candidate from the research below. Call submit_candidate. found must be false unless evidence is reliable. source is gmail only when a Gmail snippet supports it; otherwise web_search.\n\n${groundedText}` }] }],
    tools: [{ functionDeclarations: [{
      name: "submit_candidate",
      description: "Submit the venue candidate supported by the research.",
      parameters: {
        type: "OBJECT",
        properties: {
          found: { type: "BOOLEAN" }, candidate: { type: "STRING" },
          source: { type: "STRING", enum: ["gmail", "web_search"] },
        },
        required: ["found", "candidate", "source"],
      },
    }] }],
    toolConfig: { functionCallingConfig: { mode: "ANY", allowedFunctionNames: ["submit_candidate"] } },
    generationConfig: { temperature: 0 },
  }, deps.geminiKey);
  const args = responseFunctionArgs(extracted, "submit_candidate");
  const candidate = String(args.candidate || "").trim();
  const source = args.source === "gmail" ? "gmail" : "web_search";
  return args.found && candidate ? { found: true, candidate, source } : empty;
}

function closedAskMessage(event, candidate, replyToken) {
  return {
    text: `📍 “${event.summary || "your event"}” は ${candidate} で開催ですか？`,
    extra: { reply_markup: { inline_keyboard: [[
      { text: "はい", callback_data: `ask:yes:${event.id}:${replyToken}` },
      { text: "いいえ", callback_data: `ask:no:${event.id}:${replyToken}` },
    ]] } },
  };
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
          source: { type: "STRING", enum: ["location_field", "description", "web_search"], description: "Where the physical venue was resolved from." },
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
`You are Life Manager. Decide whether this calendar event requires the user to TRAVEL to an external
place, and if so where — so travel time can be planned without bothering them. Reason about the event
like a thoughtful assistant; do not pattern-match keywords. Three outcomes via submit_answer:
1. NO TRAVEL (online=true): the event needs no journey to an external venue. This covers, IN ANY LANGUAGE:
   (a) any call / online / remote / video meeting — Zoom, Meet, Teams, 電話, オンライン, リモート, ビデオ通話,
   or a clearly virtual meeting (even a terse "Zoom sync", or a bare app name). A virtual-call signal makes
   it NO TRAVEL EVEN IF a person is named — "藤井さんと電話オンライン" / "1on1 over Zoom" is still a call, NOT
   an ask. (b) ANY solo personal activity with no external venue and no external person to meet —
   sleep/睡眠, a workout/run/ランニング, meditation/瞑想, yoga/ヨガ, stretching, journaling, study/勉強,
   gym, meals at home, a focus or remote-work block. Solo wellness/self-care (meditation/瞑想, yoga,
   breathing) is done at home by DEFAULT → NO TRAVEL unless a studio/temple/venue is EXPLICITLY named in
   the title. A bare one-word or generic activity title with nowhere and no person implied is NO TRAVEL by
   DEFAULT — do NOT search, do NOT ask where a personal routine happens. No location, no question.
2. PHYSICAL & FOUND (online=false, confident=true, location=<exact address>): it genuinely happens at a
   real external venue. Use places_search (try variations: bare name, name+area, EN/JA, add the user's
   home city to disambiguate; resolve an institution/company/room name like "MUIT 出社" or a class room
   to its real building address) and return the exact formatted_address.
3. UNKNOWN (online=false, confident=false): ONLY when it is a REAL IN-PERSON meetup that genuinely needs a
   venue you cannot find AND has NO virtual-call signal — a vague external activity meant to happen somewhere
   out ("lunch with X", "1on1 with X" with no Zoom/online, "drinks") with no findable place, OR a place only
   the user knows ("おばあちゃんの家"). A SOLO routine is NEVER unknown; a virtual call is NEVER unknown. When
   torn between NO TRAVEL and UNKNOWN for a solo activity or anything with an online/call signal, choose NO TRAVEL.

Canonical examples (match the SPIRIT, reason like these — do not keyword-match):
- "藤井さんと電話オンライン" / "Zoom sync" / "電話 with X" / "Meet link" → NO TRAVEL: a virtual call.
- "Sleep" / "睡眠" / "Morning run" / "ランニング" / "Meditation" / "瞑想" / "勉強" / "Day job (remote)" →
  NO TRAVEL: a solo routine, no external venue — never ask where it is.
- "MUIT 出社" → PHYSICAL: search the company's office building → its real address.
- "[NAIST] class @ 情報科学大講義室" → PHYSICAL: resolve the institution to its campus address.
- "Lunch with Mai" / "1on1" / "おばあちゃんの家" → UNKNOWN: a real external meetup/place no search finds → ask.

Event title: ${JSON.stringify(event.summary || "")}
Event location field (may be a room name, a URL, or empty): ${JSON.stringify(event.location || "")}
Event description: ${JSON.stringify(event.description || "")}
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
        if (a.confident && a.location && String(a.location).trim()) {
          const resolvedFrom = ["location_field", "description", "web_search"].includes(a.source) ? a.source : "web_search";
          return { kind: "filled", location: String(a.location).trim(), resolvedFrom };
        }
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

async function listEvents48h(uid, key, nowMs, gmailAccountId) {
  return getCalendar({ apiKey: key, gmailAccountId }).listEventsRaw(uid, {
    timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(nowMs + 48 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
}
async function patchEvent(uid, eventId, patch, key, gmailAccountId) {
  return getCalendar({ apiKey: key, gmailAccountId }).patchEvent(uid, { calendar_id: "primary", event_id: eventId, ...patch });
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
// ATOMIC claim of an ask (C-H1) — mirrors claimWake. INSERT relies on lm_ask_log UNIQUE(uid,event_id):
// 201 = first claimer (proceed to send); 409 = already asked (skip). Race-safe; no SELECT-then-POST window.
// If supa is unconfigured, return true (don't block) — matches the pre-ledger best-effort behaviour.
async function claimAsk(uid, eventId, supaUrl, supaKey, replyToken, metadata = {}) {
  if (!supaUrl || !supaKey) return true;
  const row = { uid, event_id: eventId };
  if (replyToken) row.reply_token = replyToken; // ties the email reply (reply+<token>@) back to this event
  if (metadata.candidate) row.candidate_location = metadata.candidate;
  if (metadata.resolvedFrom) row.resolved_from = metadata.resolvedFrom;
  const r = await fetch(`${supaUrl}/rest/v1/lm_ask_log`, {
    method: "POST",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify(row),
  }).catch(() => null);
  return !!r && r.status === 201; // 201 inserted (claimed) | 409 duplicate (already asked)
}
// Release a claim when the ask SEND failed, so a later tick retries (claim→send→unclaim-on-failure).
async function unclaimAsk(uid, eventId, supaUrl, supaKey) {
  if (!supaUrl || !supaKey) return;
  await fetch(`${supaUrl}/rest/v1/lm_ask_log?uid=eq.${encodeURIComponent(uid)}&event_id=eq.${encodeURIComponent(eventId)}`, {
    method: "DELETE",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, Prefer: "return=minimal" },
  }).catch(() => {});
}

async function recordResolution(uid, eventId, source, supaUrl, supaKey) {
  if (!uid || !eventId || !source || !supaUrl || !supaKey) return;
  await fetch(`${supaUrl}/rest/v1/lm_ask_log?on_conflict=uid,event_id`, {
    method: "POST",
    headers: {
      apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify({ uid, event_id: eventId, resolved_from: source }),
  }).catch(() => {});
}

// recallOrResolve(event, opts) → { kind:"filled"|"online"|"ask", location?, fromMemory? }. Checks remembered
// memory FIRST (REQ-45: a hit returns filled WITHOUT calling the model); else the agentic resolution. recall
// + resolve are injectable so the recall-no-model invariant has an executable test (FIND-001/004).
async function recallOrResolve(event, opts) {
  const recall = opts.recall || recallPlace;
  const resolve = opts.resolve || agentResolveLocation;
  const mem = await recall(opts.uid, placeKey(event.summary), opts.supaUrl, opts.supaKey);
  if (mem) return { kind: "filled", location: mem, fromMemory: true };
  return await resolve(event, { home: opts.home, mapsKey: opts.mapsKey, geminiKey: opts.geminiKey });
}

// Returns { autofilled, asked, resolved }.
async function askTick(uid, opts) {
  const { composioKey, userEmail, resendKey, supaUrl, supaKey, mapsKey, geminiKey } = opts;
  const nowMs = opts.nowMs || Date.now();
  // Injectable (default to the real impls) so the ask-vs-autofill decision is unit-testable without
  // hitting the calendar transport / Supabase over the network — same DI pattern as recall/resolve above.
  const listEvents = opts.listEvents || listEvents48h;
  const getAskedSet = opts.askedSet || askedSet;
  const patch = opts.patchEvent || patchEvent;
  const record = opts.recordResolution || recordResolution;
  let autofilled = 0, asked = 0, resolved = 0;
  const events = await listEvents(uid, composioKey, nowMs, opts.gmailAccountId);
  const already = await getAskedSet(uid, supaUrl, supaKey);

  // For EVERY event still missing a location, let the agent RESOLVE it again every tick — the agent may
  // now succeed where a past tick asked (better search / a newer model). We dedup only the ASK SEND
  // (don't email/Telegram the same event twice), NOT the resolve attempt — that's what kept "MUIT 出社"
  // permanently unfilled after one old ask. (Dais 2026-06-23: the agent must keep doing the work.)
  for (const event of events.filter((e) => needsLocation(e))) {
    // PC-1 (C3 REQ-45): memory FIRST (a hit fills WITHOUT calling the model, never asks); else agentic resolve.
    const res = await recallOrResolve(event, {
      uid, supaUrl, supaKey, home: opts.home, mapsKey, geminiKey,
      recall: opts.recall, resolve: opts.resolve,
    });
    if (res.kind === "online") {
      continue; // online/remote/phone → no place, no travel, never ask. (No mark: re-classify is cheap.)
    }
    if (res.kind === "filled") {
      await patch(uid, event.id, { location: res.location }, composioKey, opts.gmailAccountId);
      await record(uid, event.id, res.fromMemory ? "location_field" : (res.resolvedFrom || "web_search"), supaUrl, supaKey);
      autofilled++; // location now set → needsLocation=false next tick → drops out of this loop
      continue;
    }
    // res.kind === "ask" — resolveLocation alone couldn't place it. ATOMIC dedup (C-H1): CLAIM before
    // sending so two concurrent ticks can't double-ask; release the claim if the send fails.
    if (already.has(event.id)) continue; // fast-path: known-asked this tick → skip
    // Before bothering the user, let the agent search Gmail/web for evidence (life-manager#11: asking is
    // the failure mode, not the fallback of first resort — a found candidate autofills directly, same as
    // the "filled" branch above). Only a genuinely unresolvable event reaches the actual ask below.
    const candidate = await agentSearchCandidate(event, {
      geminiKey, geminiRaw: opts.geminiRaw, mail: opts.mail,
      gmailAccountId: opts.gmailAccountId, unipileToken: opts.unipileToken, unipileDsn: opts.unipileDsn,
    });
    if (candidate.found) {
      await patch(uid, event.id, { location: candidate.candidate }, composioKey, opts.gmailAccountId);
      await record(uid, event.id, candidate.source || "web_search", supaUrl, supaKey);
      autofilled++;
      continue;
    }
    // ASK: prefer Telegram when the user linked it (replies come back via the /telegram webhook); otherwise
    // email from OUR domain via Resend, with a short opaque token in the Reply-To (reply+<token>@reply.
    // aniccaai.com). The reply lands on /inbound-email, which looks the token up in lm_ask_log and patches
    // this event. We NEVER read the user's Gmail. CLAIM (with the token) before sending so two ticks can't
    // double-ask; release the claim if the send fails so a later tick retries.
    const replyToken = newReplyToken();
    if (!(await claimAsk(uid, event.id, supaUrl, supaKey, replyToken, {}))) continue;
    let sent = false;
    if (opts.telegramChatId && opts.telegramToken) {
      const r = await tgSend(opts.telegramToken, opts.telegramChatId,
        `📍 Where is “${event.summary || "your event"}”? Just reply here and I’ll add it to your calendar.`);
      sent = !!(r && r.ok);
    } else if (userEmail && resendKey) {
      const r = await sendAsk({ to: userEmail, replyToken, event, resendKey });
      sent = !!(r && r.sent);
    }
    if (sent) asked++;
    else await unclaimAsk(uid, event.id, supaUrl, supaKey); // send failed → release so next tick retries
  }

  // Replies (email + Telegram) both arrive via webhooks now — Telegram → /telegram, email → /inbound-email.
  // Neither polls an inbox, so there is no read step here.
  return { autofilled, asked, resolved };
}

// Handle one inbound email reply (from /inbound-email). The Reply-To token resolves to (uid, event_id) via
// lm_ask_log; we fetch that event, let the model extract the location the user gave, patch the calendar, and
// remember it so a future same-summary event autofills. Returns { ok, uid, eventId, location } | { ok:false }.
// Pull the reply+<token> out of a Resend Inbound payload, tolerating every recipient shape Resend may send:
// {to:"a@b"} | {to:[{address}]} | {to:[{email}]} | {to:["a@b"]} | {data:{...}} wrapper + cc/headers.to.
// Returns { token, text } | { token:null }. Pure — unit-tested for all shapes (vcsdd FIND-001).
function parseInboundRecipient(payload) {
  const d = (payload && payload.data) || payload || {};
  const recips = []
    .concat(d.to || [], d.cc || [], (d.headers && d.headers.to) || [])
    .flatMap((x) => (typeof x === "string" ? x : (x && (x.address || x.email)) || ""));
  const addr = recips.find((a) => /reply\+[A-Za-z0-9_-]+@/.test(a)) || "";
  const m = addr.match(/reply\+([A-Za-z0-9_-]+)@/);
  return { token: (m && m[1]) || null, text: d.text || d.subject || "" };
}

// Atomically CONSUME an unanswered ask token (flip answered_at null→now). Returns the (uid,event_id) row IF
// THIS call won the flip, else null — so a replayed/duplicate inbound POST is a no-op (vcsdd FIND-003).
async function consumeAskToken(token, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  const r = await f(`${supaUrl}/rest/v1/lm_ask_log?reply_token=eq.${encodeURIComponent(token)}&answered_at=is.null&select=uid,event_id`, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify({ answered_at: new Date().toISOString(), resolved_from: "user_answer" }),
  }).catch(() => null);
  const rows = r ? await r.json().catch(() => []) : [];
  return (Array.isArray(rows) && rows[0]) || null;
}

async function lookupAskCandidate(replyToken, eventId, supaUrl, supaKey, fetchImpl) {
  if (!replyToken || !eventId || !supaUrl || !supaKey) return null;
  const f = fetchImpl || fetch;
  const url = `${supaUrl}/rest/v1/lm_ask_log?reply_token=eq.${encodeURIComponent(replyToken)}` +
    `&event_id=eq.${encodeURIComponent(eventId)}&answered_at=is.null&select=uid,event_id,candidate_location`;
  const r = await f(url, {
    method: "PATCH",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify({ answered_at: new Date().toISOString() }),
  }).catch(() => null);
  const rows = r ? await r.json().catch(() => []) : [];
  const row = Array.isArray(rows) && rows[0];
  return row && row.candidate_location
    ? { uid: row.uid, eventId: row.event_id, candidate: row.candidate_location }
    : null;
}

async function handleAskCallback(data, opts = {}) {
  const match = String(data || "").match(/^ask:(yes|no):([^:]+):([^:]+)$/);
  if (!match) return { ok: false, ignored: true };
  const [, choice, eventId, replyToken] = match;
  if (choice === "no") {
    const text = `📍 Where is “${opts.summary || "your event"}”? Just reply here and I’ll add it to your calendar.`;
    const send = opts.sendMessage || tgSend;
    if (opts.telegramToken && opts.chatId) await send(opts.telegramToken, opts.chatId, text);
    return { ok: true, fallback: true, eventId };
  }
  const lookup = opts.lookupCandidate || ((token, id) => lookupAskCandidate(
    token, id, opts.supaUrl, opts.supaKey, opts.fetchImpl));
  const hit = await lookup(replyToken, eventId);
  if (!hit || !hit.candidate) return { ok: false, reason: "candidate not found" };
  const patch = opts.patch || ((uid, id, location) => patchEvent(uid, id, { location }, opts.composioKey, opts.gmailAccountId));
  await patch(hit.uid, hit.eventId || eventId, hit.candidate);
  if (hit.summary) {
    const remember = opts.remember || ((uid, summary, location) => rememberPlace(
      uid, placeKey(summary), location, opts.supaUrl, opts.supaKey));
    await remember(hit.uid, hit.summary, hit.candidate);
  }
  console.log(`[ask] callback yes uid=${String(hit.uid).slice(0, 12)} event=${eventId}`);
  return { ok: true, eventId, location: hit.candidate };
}

// Handle one inbound email reply. IDEMPOTENT: we atomically consume the token FIRST — only the first
// reply to win the answered_at flip resolves (uid,event); a replay/duplicate gets null and no-ops. We also
// skip if the event already has a location (a later autofill fixed it) — no overwrite (vcsdd FIND-004).
// Deps (consume/listEvents/match/patch/remember) are injectable for tests; default to the real impls.
async function handleInboundReply(token, replyText, opts = {}) {
  const { composioKey, geminiKey, supaUrl, supaKey } = opts;
  if (!token || !supaUrl || !supaKey) return { ok: false, reason: "missing token/supa" };
  const consume = opts.consume || ((t) => consumeAskToken(t, supaUrl, supaKey, opts.fetchImpl));
  const listEv = opts.listEvents || ((uid) => listEvents48h(uid, composioKey, opts.nowMs || Date.now(), opts.gmailAccountId));
  const match = opts.match || ((text, ev) => agentMatchReply(text, [ev], geminiKey));
  const patch = opts.patch || ((uid, id, loc) => patchEvent(uid, id, { location: loc }, composioKey, opts.gmailAccountId));
  const remember = opts.remember || ((uid, summary, loc) => rememberPlace(uid, placeKey(summary), loc, supaUrl, supaKey));
  const needs = opts.needsLocation || needsLocation;

  // ATOMIC CONSUME first → unknown OR already-answered token = idempotent no-op.
  const hit = await consume(token);
  if (!hit) return { ok: false, reason: "unknown or already-answered token" };
  const { uid, event_id: eventId } = hit;
  const events = await listEv(uid).catch(() => []);
  const ev = (events || []).find((e) => e.id === eventId);
  if (!ev) return { ok: false, reason: "event not found", uid, eventId };
  if (!needs(ev)) return { ok: true, uid, eventId, alreadySet: true }; // location already set → don't overwrite
  const m = await match(replyText, ev);
  if (!m || !m.location) return { ok: false, reason: "no location in reply", uid, eventId };
  await patch(uid, eventId, m.location);
  await remember(uid, ev.summary, m.location);
  return { ok: true, uid, eventId, location: m.location };
}

module.exports = {
  geminiJson,
  askTick, recallOrResolve, agentResolveLocation, agentSearchCandidate, closedAskMessage,
  agentMatchReply, claimAsk, unclaimAsk, recordResolution, handleAskCallback, lookupAskCandidate,
  handleInboundReply, parseInboundRecipient, consumeAskToken,
};
