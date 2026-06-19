// e2e-ask.js — NO-MOCK end-to-end verification of the agentic ask/reply loop against a REAL Google
// Calendar (via Composio), real Gemini (function-calling places_search), and real Unipile email.
//
// It seeds two test events on the user's actual calendar, then exercises the three legs:
//   A. AUTOFILL  — Gemini searches "松竹芸能養成所" itself → writes the address back to the real event
//   B. ASK       — "歯医者の予約" can't be resolved → one real ask email is sent from the user's Gmail
//   C. REPLY     — Gemini reads a reply → writes the given location to the real event
// Everything is cleaned up at the end (both test events deleted).
//
// Nothing is hardcoded to one country: events are seeded in UTC (Google displays them in the user's
// own zone) and the home address is read from the user's lm_users row.
//
// Run: node scripts/e2e-ask.js   (env from ~/.openclaw/.env must be exported)
"use strict";
const { agentResolveLocation, agentMatchReply } = require("../lib/ask.js");

const UID = process.env.E2E_UID || "lm_784ad279-4d2c-4274-a318-b51e38285a61";
const COMPOSIO = "https://backend.composio.dev/api/v3";
const KEY = process.env.COMPOSIO_API_KEY;

async function tool(name, args) {
  const r = await fetch(`${COMPOSIO}/tools/execute/${name}`, {
    method: "POST", headers: { "x-api-key": KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: UID, arguments: args }),
  });
  return r.json();
}
// Composio nests the Google resource under data.response_data (create/get); be tolerant.
const ev = (j) => (j.data && (j.data.response_data || j.data)) || {};
// UTC wall clock N hours from now, naive (paired with timezone:"UTC") — works for any user worldwide.
function utcIn(hoursFromNow) {
  const d = new Date(Date.now() + hoursFromNow * 3600 * 1000);
  return d.toISOString().replace(/\.\d{3}Z$/, "").replace("Z", "");
}
async function createEvent(summary, startUTC) {
  const j = await tool("GOOGLECALENDAR_CREATE_EVENT", {
    calendar_id: "primary", summary, start_datetime: startUTC,
    event_duration_minutes: 45, timezone: "UTC",
  });
  return ev(j).id;
}
// Composio has no GET_EVENT tool — read back via EVENTS_LIST (exactly what production ask.js does).
async function findEvent(id) {
  const now = Date.now();
  const j = await tool("GOOGLECALENDAR_EVENTS_LIST", {
    calendarId: "primary", singleEvents: true, orderBy: "startTime", maxResults: 50,
    timeMin: new Date(now).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(now + 3 * 86400 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
  return ((j.data || {}).items || []).find((e) => e.id === id) || {};
}
const patchLocation = (id, location) => tool("GOOGLECALENDAR_PATCH_EVENT", { calendar_id: "primary", event_id: id, location });
const deleteEvent = (id) => tool("GOOGLECALENDAR_DELETE_EVENT", { calendar_id: "primary", event_id: id });

async function userHome() {
  const r = await fetch(`${process.env.SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(UID)}&select=home_address`,
    { headers: { apikey: process.env.SUPABASE_SERVICE_ROLE_KEY, Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}` } });
  const d = await r.json().catch(() => []);
  return (Array.isArray(d) && d[0] && d[0].home_address) || "";
}

(async () => {
  const pass = [], fail = [];
  const opts = { home: await userHome(), mapsKey: process.env.LIFE_MAPS_KEY, geminiKey: process.env.GEMINI_API_KEY };
  let idA, idB;
  try {
    idA = await createEvent("松竹芸能養成所 ネタ見せ", utcIn(20));
    idB = await createEvent("歯医者の予約", utcIn(24));
    console.log("seeded A=", idA, " B=", idB, " home=", JSON.stringify(opts.home));
    if (!idA || !idB) { console.error("SEED FAILED"); process.exit(1); }

    // ── Leg A: AUTOFILL ─────────────────────────────────────────────────────────
    const evA = await findEvent(idA);
    const locA = await agentResolveLocation(evA, opts);
    console.log("A agentResolveLocation →", locA);
    if (!locA) fail.push("A: agent did NOT resolve 松竹 (expected an address)");
    else {
      await patchLocation(idA, locA);
      const after = await findEvent(idA);
      console.log("A real-calendar location after patch →", after.location);
      if (after.location) pass.push(`A AUTOFILL: 松竹 → "${after.location}" written to REAL calendar`);
      else fail.push(`A: patch didn't stick (got "${after.location}")`);
    }

    // ── Leg B: ASK ──────────────────────────────────────────────────────────────
    const evB = await findEvent(idB);
    const locB = await agentResolveLocation(evB, opts);
    console.log("B agentResolveLocation →", locB, "(expected null=ask)");
    if (locB) fail.push(`B: agent wrongly auto-filled 歯医者 with "${locB}" (should ask)`);
    else {
      const dsn = process.env.UNIPILE_DSN, token = process.env.UNIPILE_TOKEN, acc = process.env.E2E_GMAIL_ACC || "98Lv6EhZS1q11UqXeiKlRQ";
      const email = (await (await fetch(`https://${dsn}/api/v1/accounts/${acc}`, { headers: { "X-API-KEY": token, accept: "application/json" } })).json()).name;
      const sendR = await fetch(`https://${dsn}/api/v1/emails`, {
        method: "POST", headers: { "X-API-KEY": token, "Content-Type": "application/json", accept: "application/json" },
        body: JSON.stringify({ account_id: acc, to: [{ identifier: email }], subject: `[Ask][E2E] 場所を教えて — 歯医者の予約`, body: `Anicca E2E test.\n--- Event ID: ${idB}` }),
      });
      console.log("B ask-email Unipile status →", sendR.status);
      if (sendR.ok) pass.push("B ASK: 歯医者 unresolved → real ask email sent from user's Gmail (Unipile 2xx)");
      else fail.push(`B: ask email send failed (${sendR.status})`);
    }

    // ── Leg C: REPLY ────────────────────────────────────────────────────────────
    const match = await agentMatchReply("> Anicca E2E test\n渋谷の田中歯科クリニックです。よろしく", [{ id: idB, summary: "歯医者の予約" }], opts.geminiKey);
    console.log("C agentMatchReply →", JSON.stringify(match));
    if (match && match.eventId === idB && match.location) {
      await patchLocation(idB, match.location);
      const after = await findEvent(idB);
      console.log("C real-calendar location after patch →", after.location);
      if (after.location) pass.push(`C REPLY: reply read → "${after.location}" written to REAL calendar`);
      else fail.push("C: reply patch didn't stick");
    } else fail.push("C: agentMatchReply failed to match the reply to the event");
  } finally {
    if (idA) await deleteEvent(idA);
    if (idB) await deleteEvent(idB);
    console.log("cleaned up test events");
  }

  console.log("\n===== E2E RESULT =====");
  pass.forEach((p) => console.log("✅", p));
  fail.forEach((f) => console.log("❌", f));
  process.exit(fail.length ? 1 : 0);
})();
