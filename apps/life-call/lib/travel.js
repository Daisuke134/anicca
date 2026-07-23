// lib/travel.js — cloud travel-time auto-fill. For a user, look at today→+7d of located events and
// insert a "[Travel]" block before each one so the wake call fires before they must LEAVE. Ports
// travel/travel_fill.py to the Railway service: Google Directions for the leave time, Composio for the
// gcal read + write. Origin priority: previous event's location (back-to-back) → the user's home.
// Idempotent: never inserts a second [Travel] for an event that already has one.
"use strict";

const { getCalendar } = require("./transport/index.js");
const { chooseRouter, parseTransitPlan } = require("./transit.js");
const { makeRouteCache, timeBucket } = require("./route-cache.js");
const { interpretCalendarEvent } = require("./calendar-interpreter.js");

// C3 (FIND-002): a process-lifetime route-result cache so the 60s scheduler tick does NOT recompute a
// route it already has (~30 paid provider calls/event → 1). Keyed on (from_geo, to_geo, time_bucket).
const _routeCache = makeRouteCache({ store: new Map(), ttlMs: 10 * 60_000 });

function isoNaiveUTC(ms) {
  // Timezone-agnostic: pass the UTC wall clock paired with timezone:"UTC" (set in createTravelBlock).
  // Google stores the correct ABSOLUTE instant and shows it in each user's own timezone — so this
  // works for a user in Tokyo, New York, or anywhere, with no hardcoded offset.
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "").replace("Z", "");
}
function isTravel(summary) {
  const s = summary || "";
  return s.startsWith("[Travel]") || s.includes("🚆 移動");
}

// PURE travel decision — geometry only (origin selection + home→home guard). It does NOT judge whether
// an event is "online": that is the AGENT's call (agentResolveLocation, ask.js), made via prompt+tools,
// never a hardcoded keyword regex (Dais 2026-06-23: ~/.claude/rules/building-effective-ai-agents.md —
// "no brittle if-else hardcoded logic; the model decides"). An online event surfaces here as an
// un-routable location → fillTravel asks the agent, which returns kind:"online" → skipped.
// Returns { insert: boolean, origin: string|null, reason: string }.
function travelDecision(ev, prev, home) {
  const norm = (s) => (s || "").replace(/\s+/g, "").toLowerCase();
  if (!ev || isTravel(ev.summary) || !((ev.location || "").trim())) {
    return { insert: false, origin: null, reason: "helper-or-no-location" };
  }
  // Origin = previous event's location if it ends within [0,90] min before this one (back-to-back) AND
  // the previous event is a REAL event (not one of Anicca's own [Travel] helper blocks); else home.
  const gap = prev && prev.endMs ? ev.startMs - prev.endMs : Infinity;
  const origin = prev && prev.location && !isTravel(prev.summary) && gap >= 0 && gap <= 90 * 60000
    ? prev.location : home;
  if (!origin) return { insert: false, origin: null, reason: "no-origin" }; // home unknown → ask-loop handles it
  if (norm(origin) === norm(ev.location)) return { insert: false, origin, reason: "same-location" }; // home→home etc.
  return { insert: true, origin, reason: "travel-needed" };
}
function shortName(addr) {
  return (addr || "").split(/[,、]/)[0].slice(0, 18) || "?";
}

async function listEvents7d(uid, apiKey, nowMs, calendar, gmailAccountId) {
  const cal = calendar || getCalendar({ apiKey, gmailAccountId });
  const items = await cal.listEventsRaw(uid, {
    timeMin: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    timeMax: new Date(nowMs + 7 * 86400 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  });
  return items.filter((e) => interpretCalendarEvent(e).decision !== "no_call").map((e) => ({
    id: e.id || "",                                   // C-H1: stable per-event key for the atomic claim ledger
    summary: e.summary || "",
    location: e.location || "",
    startIso: (e.start || {}).dateTime || "",
    startMs: Date.parse((e.start || {}).dateTime || ""),
    endMs: Date.parse((e.end || {}).dateTime || ""),
  })).filter((e) => Number.isFinite(e.startMs));
}

// ── #71 Routes API helpers (pure, unit-tested in travel-routes.test.js) ──────────────────────────
// DRIVE now uses Routes API computeRoutes with TRAFFIC_AWARE_OPTIMAL — REAL traffic, so the old ×1.4
// fudge is GONE. TRANSIT stays on legacy Directions: VERIFIED 2026-06-21 that Routes API TRANSIT
// returns no routes for our key/region (empty {} even between major stations), while legacy transit
// works. departureTime ≈ event start so we get the traffic the user will actually hit (never-late bias).
function parseDurationSeconds(s) {
  const m = /^(\d+)s$/.exec(String(s || "").trim());
  return m ? Number(m[1]) : null;
}
function minutesFromSeconds(sec) {
  if (!Number.isFinite(sec)) return null;
  return Math.max(5, Math.round(sec / 60));
}

// Shared provider acceptance contract for the production route fallback and readiness preflight.
// Either valid provider keeps routing operational; when both work, preserve the never-late max bias.
function acceptRouteResults({ legacyTransit, routesDrive }) {
  const providers = [
    ["legacy_transit", legacyTransit],
    ["routes_drive", routesDrive],
  ];
  const availableProviders = providers.filter(([, value]) => Number.isFinite(value)).map(([name]) => name);
  const degradedProviders = providers.filter(([, value]) => !Number.isFinite(value)).map(([name]) => name);
  const values = providers.map(([, value]) => value).filter(Number.isFinite);
  return {
    operational: values.length > 0,
    minutes: values.length ? Math.max(...values) : null,
    availableProviders,
    degradedProviders,
  };
}
function buildDriveBody(src, dst, departIso) {
  return {
    origin: { address: src }, destination: { address: dst },
    travelMode: "DRIVE", routingPreference: "TRAFFIC_AWARE_OPTIMAL", departureTime: departIso,
  };
}
function clampDepartIso(departAtMs, nowMs) {
  // Routes API rejects a departureTime in the past → floor to now+60s.
  const ms = Math.max(Number(departAtMs) || 0, (Number(nowMs) || 0) + 60000);
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function routesDriveMinutes(src, dst, mapsKey, departAtMs, nowMs) {
  const body = JSON.stringify(buildDriveBody(src, dst, clampDepartIso(departAtMs, nowMs)));
  try {
    const r = await fetch("https://routes.googleapis.com/directions/v2:computeRoutes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": mapsKey,
        "X-Goog-FieldMask": "routes.duration",
      },
      body,
    });
    if (!r.ok) return null;
    const j = await r.json();
    const sec = parseDurationSeconds((((j.routes || [])[0]) || {}).duration);
    return sec == null ? null : minutesFromSeconds(sec);
  } catch { return null; }
}

// arriveByMs: used for outbound (arrive-by event start). departAtMs: used for return legs (depart at
// event end). Only one should be non-null; if neither is a future time, falls back to departure_time="now".
async function legacyTransitMinutes(src, dst, mapsKey, arriveByMs, nowMs = Date.now(), departAtMs = null) {
  const p = new URLSearchParams({ origin: src, destination: dst, mode: "transit", key: mapsKey });
  // NEVER-LATE: anchor transit to the EVENT, not "now". Future event → arrival_time = event start, so
  // the train time reflects the schedule the user will actually ride. Past/missing → fall back to now.
  // Return leg: departAtMs is set → use departure_time anchored to event end (FIND-004).
  if (Number.isFinite(departAtMs) && departAtMs > nowMs) {
    p.set("departure_time", String(Math.floor(departAtMs / 1000)));
  } else if (Number.isFinite(arriveByMs) && arriveByMs > nowMs) {
    p.set("arrival_time", String(Math.floor(arriveByMs / 1000)));
  } else {
    p.set("departure_time", "now");
  }
  try {
    const r = await fetch(`https://maps.googleapis.com/maps/api/directions/json?${p}`);
    const j = await r.json();
    if (j.status !== "OK" || !j.routes || !j.routes[0] || !j.routes[0].legs || !j.routes[0].legs[0]) return null;
    return minutesFromSeconds(j.routes[0].legs[0].duration.value);
  } catch { return null; }
}

// Query BOTH transit (anchored to event start) and traffic-aware drive, then take the LARGER —
// never-late bias: we don't yet know the user's mode, so assume the slower so we never under-estimate.
// departAtMs ≈ event start. Returns null only if neither mode resolves (caller then asks). floor 5 min.
// TODO(#69/#70): per-user travel_mode preference → trust the chosen mode instead of max().
//
// departureMode: when true, the time arg is a DEPARTURE anchor (for return legs — FIND-004).
// Outbound (default false): transit uses arrival_time = event start (arrive-by).
// Return (true): transit uses departure_time = ev.endMs (depart-at, not arrive-by).
// The Google path (Routes Pro drive + legacy transit, never-late MAX bias). This is the FALLBACK now.
async function directionsMinutesGoogle(src, dst, mapsKey, departAtMs = Date.now(), nowMs = Date.now(), departureMode = false) {
  if (!mapsKey || !src || !dst) return null;
  const [transit, drive] = await Promise.all([
    departureMode
      ? legacyTransitMinutes(src, dst, mapsKey, null, nowMs, departAtMs)
      : legacyTransitMinutes(src, dst, mapsKey, departAtMs, nowMs),
    routesDriveMinutes(src, dst, mapsKey, departAtMs, nowMs),
  ]);
  return acceptRouteResults({ legacyTransit: transit, routesDrive: drive }).minutes;
}

// C3: address→geo memo — the 60s scheduler tick must NOT re-geocode the same home/event address every
// time. Keyed on the address string; a geo rarely changes for a fixed address. Process-lifetime cache.
const _geoMemo = new Map();

// C2: geocode a JP address ONCE via Google Geocoding (cheap, one-time; NOT the Routes-Pro cost driver).
// Returns {lat,lon} or null. Injected in tests via opts._geocode.
async function geocodeAddress(addr, mapsKey) {
  if (!addr || !mapsKey) return null;
  if (_geoMemo.has(addr)) return _geoMemo.get(addr);
  try {
    const u = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(addr)}&key=${mapsKey}`;
    const j = await (await fetch(u)).json();
    const loc = j && j.results && j.results[0] && j.results[0].geometry && j.results[0].geometry.location;
    return loc ? { lat: loc.lat, lon: loc.lng } : null;
  } catch { return null; }
}

// C2: real FREE JP transit fetch (api.transit.ls8h.com /plan). Injected in tests via opts._transitFetch.
async function transitFetchPlan(srcGeo, dstGeo) {
  try {
    const u = `https://api.transit.ls8h.com/api/v1/plan?from=geo:${srcGeo.lat},${srcGeo.lon}&to=geo:${dstGeo.lat},${dstGeo.lon}`;
    return await (await fetch(u)).json();
  } catch { return null; }
}

// C2/C3 WIRE: try the FREE JP transit path first (geocode both → JP bbox → /plan), fall back to Google.
async function directionsMinutes(src, dst, mapsKey, departAtMs = Date.now(), nowMs = Date.now(), departureMode = false, opts = {}) {
  const geocode = opts._geocode || geocodeAddress;
  const transitFetch = opts._transitFetch || transitFetchPlan;
  const googleFn = opts._directionsMinutesGoogle || directionsMinutesGoogle;
  const cache = opts._routeCache || _routeCache; // tests inject a fresh cache to avoid cross-test leakage
  const google = () => googleFn(src, dst, mapsKey, departAtMs, nowMs, departureMode);
  if (!mapsKey || !src || !dst) return null;
  const [srcGeo, dstGeo] = await Promise.all([geocode(src, mapsKey), geocode(dst, mapsKey)]);
  // The expensive part = the transit/Google provider call. Cache it per (from_geo, to_geo, time_bucket)
  // so repeated 60s ticks for the same event reuse one result (FIND-002).
  const compute = async () => {
    if (srcGeo && dstGeo && chooseRouter(srcGeo, dstGeo) === "transit") {
      const plan = await transitFetch(srcGeo, dstGeo);
      const parsed = plan && parseTransitPlan(plan);
      if (parsed && parsed.durationSecs != null) return minutesFromSeconds(parsed.durationSecs);
    }
    return google(); // non-JP / unresolvable / transit empty → Google Routes (as before)
  };
  if (srcGeo && dstGeo) return cache.getOrCompute("_shared", srcGeo, dstGeo, timeBucket(departAtMs), compute);
  return compute(); // un-geocodable address → uncached (rare)
}

async function createTravelBlock(uid, apiKey, leaveMs, arriveMs, fromName, toName, dstAddr, calendar, gmailAccountId) {
  const cal = calendar || getCalendar({ apiKey, gmailAccountId });
  const hours = Math.floor((arriveMs - leaveMs) / 3600000);
  const minutes = Math.round(((arriveMs - leaveMs) % 3600000) / 60000);
  const j = await cal.createEvent(uid, {
    summary: `[Travel] 🚆 ${shortName(fromName)}→${shortName(toName)}`,
    start_datetime: isoNaiveUTC(leaveMs),
    event_duration_hour: hours, event_duration_minutes: Math.min(59, minutes),
    calendar_id: "primary", timezone: "UTC", location: dstAddr,
    description: "Auto-inserted by Anicca Life Manager — adjust if the route is wrong.",
  });
  return !!(j && j.successful);
}

// Returns { inserted, checked, skipped }. home = lm_users.home_address (may be null → first-of-day
// located events are skipped this run and should be handled by the ask-loop separately).
// _directionsMinutes: test seam — inject a stub so unit/integration tests avoid real network calls.
//   In production this is always undefined and the real directionsMinutes function is used.
// ATOMIC claim of a [Travel] leg (C-H1) — mirrors claimWake. INSERT relies on lm_travel_log
// UNIQUE(uid,event_key,leg): 201 = first claimer (create the block); 409 = another run already claimed.
// If supa is unconfigured, return true (don't block) — the in-memory gcal dedup still prevents obvious dups.
async function claimTravel(uid, eventKey, leg, supaUrl, supaKey) {
  if (!supaUrl || !supaKey) return true;
  const r = await fetch(`${supaUrl}/rest/v1/lm_travel_log`, {
    method: "POST",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ uid, event_key: eventKey, leg }),
  }).catch(() => null);
  return !!r && r.status === 201; // 201 inserted (claimed) | 409 duplicate (already created)
}
// Release a claim when createTravelBlock failed, so a later run retries (claim→create→unclaim-on-failure).
async function unclaimTravel(uid, eventKey, leg, supaUrl, supaKey) {
  if (!supaUrl || !supaKey) return;
  await fetch(`${supaUrl}/rest/v1/lm_travel_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}&leg=eq.${encodeURIComponent(leg)}`, {
    method: "DELETE",
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, Prefer: "return=minimal" },
  }).catch(() => {});
}

async function fillTravel(uid, { apiKey, mapsKey, geminiKey, home, nowMs = Date.now(), bufferMin = 5, calendar, supaUrl, supaKey, _directionsMinutes, gmailAccountId } = {}) {
  const directionsFn = _directionsMinutes || directionsMinutes;
  const cal = calendar || getCalendar({ apiKey, gmailAccountId });
  const events = await listEvents7d(uid, apiKey, nowMs, cal, gmailAccountId);
  let inserted = 0, checked = 0, skipped = 0;
  const outboundReports = [];
  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    if (isTravel(ev.summary) || !ev.location) continue;
    checked++;
    // C-H1: atomic claim key per (event, leg). Prefer the gcal event id (stable + unique). Fallback to
    // startMs:summary (NOT startMs alone — two different same-user events can share a start time, FIND-001).
    const evKey = String(ev.id || `${ev.startMs}:${ev.summary || ""}`);

    // ── OUTBOUND LEG ──────────────────────────────────────────────────────────────────────────────
    // Single source of truth for the skip/insert decision (home→home, no-origin, online, etc.).
    // Use if/else (NOT continue) so the RETURN LEG below always runs regardless of outbound fate.
    // FIND-005: the outbound continue statements must NEVER skip the return-leg evaluation.
    const decision = travelDecision(ev, events[i - 1], home);
    let outboundInserted = false;
    let resolvedDest = ev.location; // tracks the agent-resolved venue for the return leg

    if (!decision.insert) {
      skipped++;
    } else {
      const origin = decision.origin;
      // Dedup: a [Travel] block already sitting in the gap right before this event?
      const dup = events.some((e) => isTravel(e.summary) && e.endMs && e.endMs <= ev.startMs && e.endMs > ev.startMs - 3 * 3600000);
      if (dup) {
        skipped++;
        // outbound block already exists — fall through to return-leg so it can backfill a missing return block
      } else {
        let dest = ev.location;
        let mins = await directionsFn(origin, dest, mapsKey, ev.startMs, nowMs);
        if (mins == null && geminiKey) {
          // The location is a room name / unroutable string (e.g. "情報科学大講義室[L1]（IS）"). Let the
          // agent web-search the REAL venue address so a must-travel event still gets a block instead of a
          // silent skip — never-late beats clean code. (Lazy require avoids any load-order coupling.)
          try {
            const { agentResolveLocation } = require("./ask.js");
            const res = await agentResolveLocation(ev, { home, mapsKey, geminiKey });
            if (res && res.kind === "online") {
              skipped++;
              continue; // truly online — no outbound OR return block needed; skip entire iteration
            }
            if (res && res.kind === "filled" && res.location) {
              dest = res.location;
              mins = await directionsFn(origin, dest, mapsKey, ev.startMs, nowMs);
            }
          } catch { /* fall through to null-mins skip below */ }
        }
        if (mins == null) {
          skipped++;
          // Cannot route outbound — still evaluate return leg in case it is independently resolvable
        } else {
          const arriveMs = ev.startMs;
          const leaveMs = arriveMs - (mins + bufferMin) * 60000;
          if (leaveMs < nowMs) {
            skipped++; // REQ-18: past GO leave time → no outbound block; return leg still evaluated below
          } else {
            // C-H1: atomically CLAIM the GO leg before creating — two concurrent runs can't double-insert.
            if (await claimTravel(uid, evKey, "go", supaUrl, supaKey)) {
              if (await createTravelBlock(uid, apiKey, leaveMs, arriveMs, origin, dest, dest, cal, gmailAccountId)) {
                inserted++;
                outboundInserted = true;
                const sameAsHome = home && String(origin).replace(/\s+/g, "").toLowerCase() ===
                  String(home).replace(/\s+/g, "").toLowerCase();
                outboundReports.push({
                  eventId: evKey,
                  summary: ev.summary || "予定",
                  startMs: ev.startMs,
                  startIso: ev.startIso,
                  origin: sameAsHome ? "自宅" : shortName(origin),
                  leaveMs,
                  arriveMs,
                });
              } else {
                skipped++;
                await unclaimTravel(uid, evKey, "go", supaUrl, supaKey); // create failed → release for retry
              }
            } else {
              skipped++; // another writer already claimed the GO block (race-safe)
            }
          }
        }
        resolvedDest = dest; // capture agent-resolved address for the return-leg directions call
      }
    }

    // ── RETURN LEG (REQ-15, FIND-001, FIND-003, FIND-004, FIND-005) ──────────────────────────────
    // Evaluated INDEPENDENTLY of the outbound leg's fate. The three former `continue` points above
    // (decision.insert=false, outbound dedup, past-leaveMs) no longer prevent this code from running.
    //
    // Return-leg past-guard (mirrors REQ-18 for the return leg — FIND-005):
    // Skip only if ev.endMs itself is already in the past (the event is already over).
    // An event whose outbound leave-time is past but endMs is still future still gets a return block.
    if (Number.isFinite(ev.endMs) && ev.endMs <= nowMs) {
      skipped++;
      continue; // event already ended — no "head home" block needed
    }

    // returnDecision is PURE; pass events[i+1] as the "next" hint.
    const retDecision = returnDecision(ev, events[i + 1], home);
    if (!retDecision.insert) {
      skipped++;
      continue;
    }
    // Array-window dedup: scan events[] for any [Travel] return block already in the window after
    // ev.endMs. Catches both the adjacent case and the non-adjacent case (FIND-003/FIND-006):
    // a block that already exists but is NOT events[i+1] (e.g. another event sits between them).
    const retDup = events.some(
      (e) => isTravel(e.summary) && e.startMs && e.startMs >= ev.endMs && e.startMs < ev.endMs + 3 * 3600000,
    );
    if (retDup) { skipped++; continue; }
    // Compute return travel time: DEPARTURE anchored to ev.endMs (FIND-004 — departureMode=true).
    // resolvedDest is the agent-resolved venue address from the outbound leg (or ev.location if
    // outbound was skipped due to dedup/no-origin — returnDecision already checked venue non-empty).
    const venue = resolvedDest;
    if (!home) { skipped++; continue; }
    const retMins = await directionsFn(venue, home, mapsKey, ev.endMs, nowMs, /* departureMode= */ true);
    if (retMins == null) { skipped++; continue; }
    const retLeaveMs = ev.endMs;                           // depart immediately after event ends
    const retArriveMs = retLeaveMs + retMins * 60000;
    // C-H1: atomically CLAIM the RETURN leg before creating.
    if (await claimTravel(uid, evKey, "return", supaUrl, supaKey)) {
      if (await createTravelBlock(uid, apiKey, retLeaveMs, retArriveMs, venue, home, home, cal, gmailAccountId)) inserted++;
      else { skipped++; await unclaimTravel(uid, evKey, "return", supaUrl, supaKey); } // create failed → release
    } else {
      skipped++; // another writer already claimed the RETURN block (race-safe)
    }
    void outboundInserted; // suppress unused warning — used for semantic clarity only
  }
  return { inserted, checked, skipped, outboundReports };
}

// PURE return-leg decision — mirrors travelDecision geometry for the post-event leg (venue→home).
// Deterministic geometry = a TOOL-layer helper; NO LLM judgment, no keyword regex for decisions.
// Returns { insert: boolean, origin: string|null, reason: string }.
function returnDecision(ev, next, home) {
  const norm = (s) => (s || "").replace(/\s+/g, "").toLowerCase();
  // Guard: ev must exist, have an endMs, not be a [Travel] block, and have a real venue.
  if (!ev) return { insert: false, origin: null, reason: "no-event" };
  if (!Number.isFinite(ev.endMs)) return { insert: false, origin: null, reason: "no-end-time" };
  if (isTravel(ev.summary)) return { insert: false, origin: null, reason: "travel-block" };
  const venue = (ev.location || "").trim();
  if (!venue) return { insert: false, origin: null, reason: "no-location" };
  // Home must be known.
  if (!home || !(home || "").trim()) return { insert: false, origin: null, reason: "no-home" };
  // Same-location guard (reuses the identical norm() predicate from travelDecision).
  if (norm(venue) === norm(home)) return { insert: false, origin: venue, reason: "same-location" };
  // Dedup: if the immediately following slot already holds a [Travel] return block, don't insert again.
  if (next && isTravel(next.summary) && next.startMs <= ev.endMs + 60000) {
    return { insert: false, origin: venue, reason: "already-has-return-block" };
  }
  // Back-to-back check: if next exists, starts within ≤90min, AND has a real venue, the user travels
  // venue→next-venue (not home), so no return block is needed.
  const nextVenue = (next ? (next.location || "") : "").trim();
  const gap = next && Number.isFinite(next.startMs) ? next.startMs - ev.endMs : Infinity;
  if (nextVenue && gap >= 0 && gap <= 90 * 60000) {
    return { insert: false, origin: venue, reason: "next-back-to-back-venue" };
  }
  return { insert: true, origin: venue, reason: "return-needed" };
}

module.exports = {
  fillTravel, directionsMinutes, isTravel, travelDecision, returnDecision, claimTravel, unclaimTravel,
  // #71 pure helpers (unit-tested)
  parseDurationSeconds, minutesFromSeconds, buildDriveBody, clampDepartIso, acceptRouteResults,
};
