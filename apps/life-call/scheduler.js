// scheduler.js — the cloud wake loop. Every 60s: find Life Manager users due for a T-15min wake
// and place a Telnyx+Gemini-Charon call whose audio bridges back to THIS service's /ws.
//
// Source of truth:
//   lm_users (Supabase)        — registry: who has a phone + paid + a connected gcal
//   Composio connected_account — the actual Google Calendar OAuth (keyed by the SAME uid)
//   lm_wake_log (Supabase)     — dedup: one call per (uid, event start), survives restarts
"use strict";

const { fetchNextEvent } = require("./lib/events.js");
const { placeCall } = require("./lib/dial.js");

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
    `${url}/rest/v1/lm_users?select=uid,name,phone,paid,calendar_provider` +
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
  const qs = new URLSearchParams({
    summary: ev.summary || "",
    dateTime: ev.startIso || "",
    location: ev.location || "",
    urgency: urgency || "gentle",
  });
  return `${base}/ws?${qs.toString()}`;
}

async function tick() {
  const users = await supaUsers();
  const now = Date.now();
  for (const u of users) {
    let ev;
    try {
      ev = await fetchNextEvent(u.uid, { nowMs: now, horizonH: 2 });
    } catch {
      continue;
    }
    if (!ev || isHelperBlock(ev.summary)) continue;
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

module.exports = { startScheduler, tick, isHelperBlock, buildStreamUrl };
