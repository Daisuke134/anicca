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
const { shouldWake, resolveDeparture, isHelperBlock } = require("./lib/wake-filter.js");
const { placeCall } = require("./lib/dial.js");
const { fillTravel, directionsMinutes } = require("./lib/travel.js");
const { askTick } = require("./lib/ask.js");
const { onboardNudgeAll } = require("./lib/telegram-onboard.js");

// HMAC over the per-call context so the persistent /ws bridge can prove a connection was minted by
// THIS scheduler (not a stranger draining the Gemini budget) AND that the prompt context wasn't
// tampered in transit. server.js recomputes the same MAC and rejects on mismatch.
function signCtx(parts) {
  const secret = process.env.LM_CALL_SECRET || "";
  return crypto.createHmac("sha256", secret).update(parts.join("\n")).digest("base64url");
}

const TICK_MS = 60 * 1000;
// Escalating wake calls: ring at T-15 (gentle), T-10 (firm), T-5 (harsh) before EACH event — like the
// local Life Manager — so the user actually gets up / leaves. Each (event, level) fires once (deduped).
const WAKE_LEVELS = [
  { min: 15, urgency: "gentle" },
  { min: 10, urgency: "firm" },
  { min: 5, urgency: "harsh" },
];

const SUPA = () => ({ url: process.env.SUPABASE_URL, key: process.env.SUPABASE_SERVICE_ROLE_KEY });

// isHelperBlock now lives in lib/wake-filter.js (shared with the importance filter + leave anchor).

async function supaUsers() {
  const { url, key } = SUPA();
  if (!url || !key) return [];
  const base = `${url}/rest/v1/lm_users?phone=not.is.null&paid=is.true&calendar_provider=eq.composio_gcal`;
  const cols = "uid,name,phone,paid,calendar_provider,home_address,gmail_account_id,telegram_chat_id,call_language";
  const hdr = { apikey: key, Authorization: `Bearer ${key}` };
  // FAIL-SAFE: try WITH wake_policy; if the column is missing (PostgREST 400) fall back to the base
  // columns rather than returning [] — a missing column must NOT silently disable wakes fleet-wide.
  let r = await fetch(`${base}&select=${cols},wake_policy`, { headers: hdr });
  if (!r.ok) r = await fetch(`${base}&select=${cols}`, { headers: hdr }); // wake_policy → undefined → travel-only
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

// Pick the call language from the user's phone number: +81 (Japan) → Japanese, everyone else → English
// (Dais 2026-06-22). Used as the FALLBACK when the user hasn't explicitly chosen a language.
function langForPhone(phone) {
  return String(phone || "").replace(/[^\d+]/g, "").startsWith("+81") ? "ja" : "en";
}

// Resolve the call language for a user row: their EXPLICIT choice (lm_users.call_language, set via the
// /lm toggle) wins; otherwise fall back to the phone country. So a US phone can choose Japanese and a
// Japanese phone can choose English (Dais 2026-06-22).
function langForUser(u) {
  const c = u && u.call_language;
  return c === "ja" || c === "en" ? c : langForPhone(u && u.phone);
}

function buildStreamUrl(ev, urgency, lang, name) {
  const base = (process.env.PUBLIC_WSS || "").replace(/\/$/, "");
  const summary = ev.summary || "";
  const dateTime = ev.startIso || "";
  const location = ev.location || "";
  const urg = urgency || "gentle";
  const lg = lang === "ja" ? "ja" : "en";
  const nm = String(name || "").replace(/[\r\n]/g, " ").slice(0, 60); // address the user by name on the call
  const sig = signCtx([summary, dateTime, location, urg, lg, nm]); // authenticates the bridge upgrade (lang + name)
  const qs = new URLSearchParams({ summary, dateTime, location, urgency: urg, lang: lg, name: nm, sig });
  return `${base}/ws?${qs.toString()}`;
}

// ── Per-user single-invocation functions (extracted for Inngest fan-out) ─────
// Each function takes a single user row `u` and performs the loop body for THAT user only.
// The existing tick/travelTick/askTickAll still call these in a for-loop so the in-process
// LIFE_RUN_LOOPS path continues to work unchanged.

async function wakeUserOnce(u, nowMs) {
  const now = nowMs !== undefined ? nowMs : Date.now();
  let events;
  try {
    // 6h horizon: a long-travel event AND its [Travel] block must both be visible at the moment we
    // wake 15 min before DEPARTURE, which can be hours before the event itself.
    events = await fetchUpcomingEvents(u.uid, { nowMs: now, horizonH: 6 });
  } catch {
    return;
  }
  // #69 importance filter: only wake for events the user must TRAVEL to (per their wake_policy),
  // and anchor the 15/10/5 levels to DEPARTURE (leave time), not the event start — so a 30-min-travel
  // event is called before they must leave. resolveDeparture uses the [Travel] block if present, else
  // computes the leave time inline (never-late even before the 30-min travel loop inserts the block).
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  for (const ev of (events || []).filter((e) => shouldWake(e, u.home_address, u.wake_policy))) {
    const depMs = await resolveDeparture(ev, events, {
      home: u.home_address, mapsKey, nowMs: now, bufferMin: 5, directionsFn: directionsMinutes,
    });
    const mins = (depMs - now) / 60000;
    for (const lvl of WAKE_LEVELS) {
      // 60s tick → a ~2-min catch window per level; levels are 5 min apart so they never overlap.
      if (mins > lvl.min + 0.5 || mins <= lvl.min - 1.5) continue;
      const eventKey = `${u.uid}|${ev.startIso}|${lvl.min}`;
      const fresh = await claimWake(u.uid, eventKey);
      if (!fresh) continue; // already called for this (event, level)
      const streamUrl = buildStreamUrl(ev, lvl.urgency, langForUser(u), u.name);
      const res = await placeCall({ to: u.phone, streamUrl });
      if (res.ok) {
        console.log(`[scheduler] WAKE T-${lvl.min} uid=${u.uid.slice(0, 12)} "${ev.summary}" ccid=${res.ccid}`);
      } else {
        console.error(`[scheduler] dial failed T-${lvl.min} uid=${u.uid.slice(0, 12)}: ${res.error}`);
      }
    }
  }
}

// forEachUserSafe: process each tenant in ISOLATION (HARD-4). A throw/rejection while handling one user is
// caught + logged per-uid so it NEVER prevents the remaining tenants from being processed this tick. This
// mirrors the production Inngest model (each user is a separate function run); it hardens the in-process
// (LIFE_RUN_LOOPS) path to the same one-tenant-failure-can't-break-others guarantee.
async function forEachUserSafe(users, label, fn) {
  for (const u of (users || [])) {
    try {
      await fn(u);
    } catch (e) {
      const uid = (u && u.uid ? String(u.uid) : "?").slice(0, 12);
      console.error(`[${label}] uid=${uid} err ${e && e.message}`);
    }
  }
}

async function tick() {
  const users = await supaUsers();
  const now = Date.now();
  await forEachUserSafe(users, "scheduler", (u) => wakeUserOnce(u, now));
}

function startScheduler() {
  if (!process.env.PUBLIC_WSS) {
    console.warn("[scheduler] PUBLIC_WSS not set — calls would have no media bridge URL; loop still runs but won't dial");
  }
  console.log(`[scheduler] started — tick every ${TICK_MS / 1000}s, escalating wakes at T-${WAKE_LEVELS.map((l) => l.min).join("/")}min`);
  const run = () => tick().catch((e) => console.error("[scheduler] tick err", e.message));
  run();
  return setInterval(run, TICK_MS);
}

// ── Travel auto-fill (every 30 min) — keep today+7d filled with [Travel] blocks ─────────────────
const TRAVEL_TICK_MS = 30 * 60 * 1000;

async function travelUserOnce(u) {
  const apiKey = process.env.COMPOSIO_API_KEY;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  const geminiKey = process.env.GEMINI_API_KEY; // agentic resolve of room-name / unroutable locations
  if (!apiKey || !mapsKey) return;
  const { url: supaUrl, key: supaKey } = SUPA(); // C-H1: atomic [Travel] claim ledger (lm_travel_log)
  try {
    const r = await fillTravel(u.uid, { apiKey, mapsKey, geminiKey, home: u.home_address, supaUrl, supaKey });
    if (r.inserted) console.log(`[travel] uid=${u.uid.slice(0, 12)} inserted=${r.inserted} checked=${r.checked}`);
  } catch (e) {
    console.error(`[travel] uid=${u.uid.slice(0, 12)} err ${e.message}`);
  }
}

async function travelTick() {
  const apiKey = process.env.COMPOSIO_API_KEY;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey || !mapsKey) return;
  const users = await supaUsers();
  await forEachUserSafe(users, "travel", travelUserOnce);
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

async function askUserOnce(u) {
  const composioKey = process.env.COMPOSIO_API_KEY;
  const unipileToken = process.env.UNIPILE_TOKEN, unipileDsn = process.env.UNIPILE_DSN;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY; // Places grounding
  const geminiKey = process.env.GEMINI_API_KEY;                            // agentic resolve/read
  const telegramToken = process.env.LM_TELEGRAM_BOT_TOKEN;                 // Telegram ask channel
  const { url: supaUrl, key: supaKey } = SUPA();
  if (!composioKey || !supaUrl || !geminiKey) return;
  // A user is reachable for asks via Telegram OR a connected Gmail — need at least one.
  if (!u.telegram_chat_id && !u.gmail_account_id) return;
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

async function askTickAll() {
  const composioKey = process.env.COMPOSIO_API_KEY;
  const { url: supaUrl } = SUPA();
  const geminiKey = process.env.GEMINI_API_KEY;
  if (!composioKey || !supaUrl || !geminiKey) return;
  const users = await supaUsers();
  await forEachUserSafe(users, "ask", askUserOnce);
}
function startAskLoop() {
  console.log(`[ask] started — every ${ASK_TICK_MS / 60000}min`);
  const run = () => askTickAll().catch((e) => console.error("[ask] tick err", e.message));
  run();
  return setInterval(run, ASK_TICK_MS);
}

// ── Interactive Telegram onboarding nudge (every 2 min) — guide linked users to their next step ────
const ONBOARD_TICK_MS = 2 * 60 * 1000;
async function onboardTick() {
  const token = process.env.LM_TELEGRAM_BOT_TOKEN;
  const base = process.env.PUBLIC_BASE || "https://aniccaai.com";
  const { url: supaUrl, key: supaKey } = SUPA();
  if (!token || !supaUrl) return;
  const sent = await onboardNudgeAll({ token, base, supaUrl, supaKey });
  if (sent) console.log(`[onboard] nudged ${sent} Telegram user(s) to their next step`);
}
function startOnboardLoop() {
  console.log(`[onboard] started — every ${ONBOARD_TICK_MS / 60000}min (interactive Telegram guidance)`);
  const run = () => onboardTick().catch((e) => console.error("[onboard] tick err", e.message));
  run();
  return setInterval(run, ONBOARD_TICK_MS);
}

// listPaidUsers: public alias for supaUsers — used by Inngest sweep functions.
const listPaidUsers = supaUsers;

// getUserByUid: re-fetches a single user row by uid for Inngest per-user functions.
// Inngest sweepers fan-out only { uid } (PII-safe); the per-user handler calls this
// to get the full row (phone, home_address, etc.) before invoking the scheduler fn.
// Uses the same column set as supaUsers to keep behaviour identical.
async function getUserByUid(uid) {
  const { url, key } = SUPA();
  if (!url || !key || !uid) return null;
  const cols = "uid,name,phone,paid,calendar_provider,home_address,gmail_account_id,telegram_chat_id,call_language";
  const base = `${url}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&phone=not.is.null&paid=is.true&calendar_provider=eq.composio_gcal`;
  const hdr = { apikey: key, Authorization: `Bearer ${key}` };
  let r = await fetch(`${base}&select=${cols},wake_policy`, { headers: hdr });
  if (!r.ok) r = await fetch(`${base}&select=${cols}`, { headers: hdr });
  if (!r.ok) return null;
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

module.exports = {
  startScheduler, startTravelLoop, startAskLoop, startOnboardLoop,
  tick, travelTick, askTickAll, onboardTick,
  // per-user single-invocation functions (for Inngest fan-out + testing)
  wakeUserOnce, travelUserOnce, askUserOnce,
  // per-tenant isolation wrapper (HARD-4): one tenant's failure can't break the others' tick
  forEachUserSafe,
  // paid-user listing (for Inngest sweep fan-out)
  listPaidUsers,
  // per-uid re-fetch for Inngest per-user functions (PII: sweepers send only uid)
  getUserByUid,
  // utilities used by server.js and tests
  isHelperBlock, buildStreamUrl, langForPhone, langForUser,
};
