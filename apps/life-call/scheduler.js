// scheduler.js — the cloud wake loop. Every 60s: find Life Manager users due for a T-15min wake
// and place a Telnyx+Gemini-Charon call whose audio bridges back to THIS service's /ws.
//
// Source of truth:
//   lm_users (Supabase)        — registry: who has a phone + paid + a connected gcal
//   Composio connected_account — the actual Google Calendar OAuth (keyed by the SAME uid)
//   lm_wake_log (Supabase)     — dedup: one call per (uid, event start), survives restarts
"use strict";

const crypto = require("crypto");
const { fetchUpcomingEvents } = require("./lib/events.js");
const { placeCall } = require("./lib/dial.js");
const { fillTravel } = require("./lib/travel.js");
const { askTick } = require("./lib/ask.js");

// HMAC over the per-call context so the persistent /ws bridge can prove a connection was minted by
// THIS scheduler (not a stranger draining the Gemini budget) AND that the prompt context wasn't
// tampered in transit. server.js recomputes the same MAC and rejects on mismatch.
function signCtx(parts) {
  const secret = process.env.LM_CALL_SECRET || "";
  return crypto.createHmac("sha256", secret).update(parts.join("\n")).digest("base64url");
}

const TICK_MS = 60 * 1000;
const DUE_LO_MIN = 13; // fire when the event starts in [13,15] min — the 60s tick hits the window once
const DUE_HI_MIN = 15;

const SUPA = () => ({ url: process.env.SUPABASE_URL, key: process.env.SUPABASE_SERVICE_ROLE_KEY });

// Anicca's own inserted helper blocks are not real commitments — never wake someone for them.
function isHelperBlock(summary) {
  const s = summary || "";
  return s.startsWith("[Travel]") || s.includes("[PENDING]") || s.includes("[APPLIED]");
}

async function supaUsers() {
  const { url, key } = SUPA();
  if (!url || !key) return [];
  const q =
    `${url}/rest/v1/lm_users?select=uid,name,phone,paid,calendar_provider,home_address,gmail_account_id,telegram_chat_id` +
    `&phone=not.is.null&paid=is.true&calendar_provider=eq.composio_gcal`;
  const r = await fetch(q, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  if (!r.ok) return [];
  return r.json().catch(() => []);
}

// Returns true if this (uid,event_key) was NOT already called — and records it atomically.
// Relies on the unique(uid,event_key) constraint: a duplicate insert 409s → already called.
async function claimWake(uid, eventKey) {
  const { url, key } = SUPA();
  if (!url || !key) return false;
  const r = await fetch(`${url}/rest/v1/lm_wake_log`, {
    method: "POST",
    headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ uid, event_key: eventKey }),
  });
  return r.status === 201; // 201 = inserted (first time); 409 = duplicate (already called)
}

function buildStreamUrl(ev, urgency) {
  const base = (process.env.PUBLIC_WSS || "").replace(/\/$/, "");
  const summary = ev.summary || "";
  const dateTime = ev.startIso || "";
  const location = ev.location || "";
  const urg = urgency || "gentle";
  const sig = signCtx([summary, dateTime, location, urg]); // authenticates the bridge upgrade
  const qs = new URLSearchParams({ summary, dateTime, location, urgency: urg, sig });
  return `${base}/ws?${qs.toString()}`;
}

async function tick() {
  const users = await supaUsers();
  const now = Date.now();
  for (const u of users) {
    let events;
    try {
      events = await fetchUpcomingEvents(u.uid, { nowMs: now, horizonH: 2 });
    } catch {
      continue;
    }
    // Soonest REAL commitment — skip Anicca's own inserted [Travel]/[PENDING]/[APPLIED] blocks
    // (don't stop at the single soonest event; a helper block must not mask a real one behind it).
    const ev = (events || []).find((e) => !isHelperBlock(e.summary));
    if (!ev) continue;
    const mins = (ev.startMs - now) / 60000;
    if (mins < DUE_LO_MIN || mins > DUE_HI_MIN) continue;

    const eventKey = `${u.uid}|${ev.startIso}`;
    const fresh = await claimWake(u.uid, eventKey);
    if (!fresh) continue; // already called for this event

    const streamUrl = buildStreamUrl(ev, "gentle");
    const res = await placeCall({ to: u.phone, streamUrl });
    if (res.ok) {
      console.log(`[scheduler] WAKE uid=${u.uid.slice(0, 12)} "${ev.summary}" in ${Math.round(mins)}m ccid=${res.ccid}`);
    } else {
      console.error(`[scheduler] dial failed uid=${u.uid.slice(0, 12)}: ${res.error}`);
    }
  }
}

function startScheduler() {
  if (!process.env.PUBLIC_WSS) {
    console.warn("[scheduler] PUBLIC_WSS not set — calls would have no media bridge URL; loop still runs but won't dial");
  }
  console.log(`[scheduler] started — tick every ${TICK_MS / 1000}s, due window ${DUE_LO_MIN}-${DUE_HI_MIN}min`);
  const run = () => tick().catch((e) => console.error("[scheduler] tick err", e.message));
  run();
  return setInterval(run, TICK_MS);
}

// ── Travel auto-fill (every 30 min) — keep today+7d filled with [Travel] blocks ─────────────────
const TRAVEL_TICK_MS = 30 * 60 * 1000;
async function travelTick() {
  const apiKey = process.env.COMPOSIO_API_KEY;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey || !mapsKey) return;
  const users = await supaUsers();
  for (const u of users) {
    try {
      const r = await fillTravel(u.uid, { apiKey, mapsKey, home: u.home_address });
      if (r.inserted) console.log(`[travel] uid=${u.uid.slice(0, 12)} inserted=${r.inserted} checked=${r.checked}`);
    } catch (e) {
      console.error(`[travel] uid=${u.uid.slice(0, 12)} err ${e.message}`);
    }
  }
}
function startTravelLoop() {
  console.log(`[travel] started — every ${TRAVEL_TICK_MS / 60000}min, horizon 7d`);
  const run = () => travelTick().catch((e) => console.error("[travel] tick err", e.message));
  run();
  return setInterval(run, TRAVEL_TICK_MS);
}

// ── Ask/reply loop (every 20 min) — email the user about events missing a location, read replies ──
const ASK_TICK_MS = 20 * 60 * 1000;
const unipileEmailCache = new Map();
async function unipileEmail(accountId, token, dsn) {
  if (unipileEmailCache.has(accountId)) return unipileEmailCache.get(accountId);
  try {
    const r = await fetch(`https://${dsn}/api/v1/accounts/${encodeURIComponent(accountId)}`,
      { headers: { "X-API-KEY": token, accept: "application/json" } });
    const a = await r.json();
    const email = a && a.name && a.name.includes("@") ? a.name : null;
    if (email) unipileEmailCache.set(accountId, email);
    return email;
  } catch { return null; }
}
async function askTickAll() {
  const composioKey = process.env.COMPOSIO_API_KEY;
  const unipileToken = process.env.UNIPILE_TOKEN, unipileDsn = process.env.UNIPILE_DSN;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY; // Places grounding
  const geminiKey = process.env.GEMINI_API_KEY;                            // agentic resolve/read
  const telegramToken = process.env.LM_TELEGRAM_BOT_TOKEN;                 // Telegram ask channel
  const { url: supaUrl, key: supaKey } = SUPA();
  if (!composioKey || !supaUrl || !geminiKey) return;
  const users = await supaUsers();
  for (const u of users) {
    // A user is reachable for asks via Telegram OR a connected Gmail — need at least one.
    if (!u.telegram_chat_id && !u.gmail_account_id) continue;
    let userEmail = null;
    if (u.gmail_account_id && unipileToken && unipileDsn) {
      userEmail = await unipileEmail(u.gmail_account_id, unipileToken, unipileDsn);
    }
    try {
      const r = await askTick(u.uid, {
        composioKey, accountId: u.gmail_account_id, unipileToken, unipileDsn, userEmail,
        supaUrl, supaKey, mapsKey, geminiKey, home: u.home_address,
        telegramChatId: u.telegram_chat_id, telegramToken,
      });
      if (r.autofilled || r.asked || r.resolved)
        console.log(`[ask] uid=${u.uid.slice(0, 12)} autofilled=${r.autofilled} asked=${r.asked} resolved=${r.resolved} via=${u.telegram_chat_id ? "tg" : "email"}`);
    } catch (e) { console.error(`[ask] uid=${u.uid.slice(0, 12)} err ${e.message}`); }
  }
}
function startAskLoop() {
  console.log(`[ask] started — every ${ASK_TICK_MS / 60000}min`);
  const run = () => askTickAll().catch((e) => console.error("[ask] tick err", e.message));
  run();
  return setInterval(run, ASK_TICK_MS);
}

module.exports = { startScheduler, startTravelLoop, startAskLoop, tick, travelTick, askTickAll, isHelperBlock, buildStreamUrl };
