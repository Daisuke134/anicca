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

// Parse an /api/v1/plan response into the shape the wake/travel logic needs.
// Returns null when there are no journeys → caller falls back to Google.
function parseTransitPlan(plan) {
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
  return {
    durationSecs: (best.durationSecs || 0) + access,
    inVehicleSecs: best.durationSecs,
    transferCount: best.transferCount || 0,
    legs: (best.legs || []).map((l) => ({
      kind: l.kind,
      mode: l.mode,
      routeName: l.routeName,
      from: l.from && l.from.name,
      to: l.to && l.to.name,
    })),
  };
}

module.exports = { isJapanGeo, chooseRouter, parseTransitPlan, JP_BBOX };
