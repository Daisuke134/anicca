// lib/transit.js — C2 (VCSDD life-manager-cost-connect-reliability): FREE Japan public-transit router
// via api.transit.ls8h.com, replacing Google Routes Pro (premium) for JP journeys to cut cost.
//
// This module is PURE decision + parse logic (the model/agent does no judgment here — JP-vs-not is a
// deterministic geo-bbox, per building-effective-ai-agents "regex/bbox for a fixed machine format = ok,
// judgment goes to the agent"). Network fetch + caching live in the caller (C3 lm_route_cache).
//
// Terms (transit.ls8h.com/terms): free, UNOFFICIAL, no SLA → the caller MUST cache + retry + fall back
// to Google; this module only shapes the response and picks the router.
"use strict";

// Japan bounding box (inclusive). Covers Okinawa (lat ~24, lon ~123) to Hokkaido/Nemuro (~45.5, ~146).
// /plan returns walk-only journeys even outside Japan (verified: NYC → 1 journey), so a returned
// journey is NOT proof of JP — the bbox is the authoritative gate.
const JP_BBOX = { latMin: 24, latMax: 46, lonMin: 122, lonMax: 146 };

function isJapanGeo(lat, lon) {
  return (
    typeof lat === "number" &&
    typeof lon === "number" &&
    lat >= JP_BBOX.latMin &&
    lat <= JP_BBOX.latMax &&
    lon >= JP_BBOX.lonMin &&
    lon <= JP_BBOX.lonMax
  );
}

// Pick the router: transit only when BOTH endpoints are inside Japan; any non-JP/mixed → Google.
function chooseRouter(fromGeo, toGeo) {
  const jp =
    fromGeo && toGeo && isJapanGeo(fromGeo.lat, fromGeo.lon) && isJapanGeo(toGeo.lat, toGeo.lon);
  return jp ? "transit" : "google";
}

function validTimezone(timezone) {
  const zone = String(timezone || "UTC");
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone }).format(0);
    return zone;
  } catch {
    return "UTC";
  }
}

function dateKey(value) {
  const raw = String(value || "");
  if (/^\d{8}$/u.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  if (/^\d{4}-\d{2}-\d{2}$/u.test(raw)) return raw;
  return null;
}

function zonedWallInstant(date, seconds, timezone) {
  const key = dateKey(date);
  const total = Number(seconds);
  if (!key || !Number.isFinite(total)) return null;
  const [year, month, day] = key.split("-").map(Number);
  const wallMs = Date.UTC(year, month - 1, day) + total * 1000;
  const zone = validTimezone(timezone);
  let instant = wallMs;
  for (let pass = 0; pass < 3; pass += 1) {
    const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
      timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]));
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
      Number(parts.hour), Number(parts.minute), Number(parts.second));
    instant = wallMs - (represented - instant);
  }
  return new Date(instant).toISOString();
}

function modeForStep(mode, kind) {
  if (kind === "walk" || mode === "walk") return "walk";
  if (mode === "rail") return "train";
  if (mode === "subway") return "subway";
  if (mode === "bus") return "bus";
  if (kind === "transfer") return "transfer";
  return mode || "other";
}

function nullableNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

// Parse an /api/v1/plan response into a structured, provider-fact-preserving
// route. Returns null when there are no journeys → caller falls back to Google.
function parseTransitPlan(plan, anchor = {}) {
  const journeys = (plan && Array.isArray(plan.journeys) && plan.journeys) || [];
  if (journeys.length === 0) return null;
  // Best = earliest arrival (the fixture is departure-sorted; arrival is the honest "you're there by").
  const best = journeys.reduce((a, b) => (b.arrivalSecs < a.arrivalSecs ? b : a));
  // NEVER-LATE door-to-door (FIND-004 + FIND-101): the journey's durationSecs = arrivalSecs − departureSecs,
  // where arrivalSecs ALREADY includes the egress walk (journey arrival = last-leg arrival + egressWalk,
  // verified against the fixture: 81789 − 81660 = 129 = egressWalkSecs). departureSecs = first-leg (train)
  // departure, so the ACCESS walk to the first stop is NOT yet included. Door-to-door = accessWalk + duration.
  // Adding egress again would double-count it.
  const access = Number(best.accessWalkSecs) || 0;
  const egress = nullableNumber(best.egressWalkSecs);
  const timezone = validTimezone((plan && plan.timezone) || anchor.timezone || "UTC");
  const date = (plan && plan.date) || anchor.date || null;
  const fare = best.fare == null ? null : best.fare;
  const legs = Array.isArray(best.legs) ? best.legs : [];
  const steps = legs.map((leg) => {
    const from = leg && leg.from && leg.from.name != null ? String(leg.from.name) : null;
    const to = leg && leg.to && leg.to.name != null ? String(leg.to.name) : null;
    const departureSecs = nullableNumber(leg && leg.departureSecs);
    const arrivalSecs = nullableNumber(leg && leg.arrivalSecs);
    const durationSeconds = nullableNumber(leg && leg.durationSecs)
      ?? (departureSecs != null && arrivalSecs != null ? arrivalSecs - departureSecs : null);
    const geometry = leg && leg.geometry != null ? leg.geometry : null;
    return {
      mode: modeForStep(leg && leg.mode, leg && leg.kind),
      instruction: leg && leg.instruction != null ? String(leg.instruction) : null,
      from,
      to,
      service: leg && (leg.service || leg.routeName) != null ? String(leg.service || leg.routeName) : null,
      headsign: leg && leg.headsign != null ? String(leg.headsign) : null,
      platform: leg && (leg.platform == null ? leg.platformCode : leg.platform) != null
        ? String(leg.platform == null ? leg.platformCode : leg.platform) : null,
      departAt: zonedWallInstant(date, departureSecs, timezone),
      arriveAt: zonedWallInstant(date, arrivalSecs, timezone),
      durationSeconds,
      geometry,
    };
  });
  const hasPlatform = steps.some((step) => step.platform != null);
  const hasGeometry = steps.some((step) => step.geometry != null);
  const provider = plan && plan.provider ? String(plan.provider) : "transit";
  return {
    provider,
    computedAt: plan && (plan.computedAt || plan.computed_at) || null,
    timezone,
    departureAt: zonedWallInstant(date, best.departureSecs, timezone),
    arrivalAt: zonedWallInstant(date, best.arrivalSecs, timezone),
    durationSeconds: (best.durationSecs || 0) + access,
    accessWalkSeconds: access,
    egressWalkSeconds: egress,
    fare,
    steps,
    availability: { platform: hasPlatform, fare: fare != null, geometry: hasGeometry },
    date: dateKey(date),
    departureSecs: best.departureSecs,
    arrivalSecs: best.arrivalSecs,
    durationSecs: (best.durationSecs || 0) + access,
    inVehicleSecs: best.durationSecs,
    accessWalkSecs: access,
    egressWalkSecs: egress,
    transferCount: best.transferCount || 0,
    legs: legs.map((l) => ({
      kind: l.kind,
      mode: l.mode,
      routeName: l.routeName,
      service: l.service,
      from: l.from && l.from.name,
      to: l.to && l.to.name,
      headsign: l.headsign,
      platform: l.platform == null ? l.platformCode : l.platform,
      departureSecs: l.departureSecs,
      arrivalSecs: l.arrivalSecs,
      geometry: l.geometry == null ? null : l.geometry,
    })),
  };
}

module.exports = { isJapanGeo, chooseRouter, parseTransitPlan, zonedWallInstant, dateKey, JP_BBOX };
