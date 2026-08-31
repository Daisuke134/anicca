"use strict";
// lib/care-anchors.js — 11b PHY-b (§10 row 11b): derive the user's 生活圏 anchors
// (home / work / usual providers) from their OWN data, so care-candidate search
// is bound to where the user actually lives — never a hand-fed list that could
// book a Kyoto barber for a Tokyo user. Pure module: no I/O, no clock, no env.

const WORK_MIN_OCCURRENCES = 3; // fewer repeats of a place is a visit, not a workplace
const USUAL_MIN_VISITS = 2; // one visit is a trial, two is a habit

// Frequency table keyed by a string; each entry tracks count + most recent startMs
// so ties always break toward the place the user went to most recently.
function tally(map, key, startMs) {
  const entry = map.get(key) || { count: 0, latestMs: -Infinity };
  entry.count += 1;
  const ms = Number.isFinite(startMs) ? startMs : -Infinity;
  if (ms > entry.latestMs) entry.latestMs = ms;
  map.set(key, entry);
}

function pickMostFrequent(map, minCount) {
  let bestKey = null;
  let best = null;
  for (const [key, entry] of map) {
    if (entry.count < minCount) continue;
    if (!best
      || entry.count > best.count
      || (entry.count === best.count && entry.latestMs > best.latestMs)) {
      best = entry;
      bestKey = key;
    }
  }
  return bestKey;
}

function deriveAnchors({ homeAddress = null, calendarEvents = [], careHistory = [] } = {}) {
  const home = typeof homeAddress === "string" && homeAddress.trim() ? homeAddress : null;
  const homeKey = home ? home.trim() : null;

  // work = most frequent non-home location across calendar events.
  const locations = new Map();
  for (const event of Array.isArray(calendarEvents) ? calendarEvents : []) {
    const location = typeof event?.location === "string" ? event.location.trim() : "";
    if (!location || location === homeKey) continue;
    tally(locations, location, event.startMs);
  }
  const work = pickMostFrequent(locations, WORK_MIN_OCCURRENCES);

  // usualProviders = per careType, the location the user actually returns to.
  const byType = new Map();
  for (const visit of Array.isArray(careHistory) ? careHistory : []) {
    const careType = typeof visit?.careType === "string" ? visit.careType.trim() : "";
    const location = typeof visit?.location === "string" ? visit.location.trim() : "";
    if (!careType || !location) continue;
    if (!byType.has(careType)) byType.set(careType, new Map());
    tally(byType.get(careType), location, visit.startMs);
  }
  const usualProviders = [];
  for (const careType of [...byType.keys()].sort()) {
    const location = pickMostFrequent(byType.get(careType), USUAL_MIN_VISITS);
    if (location) usualProviders.push({ careType, location });
  }

  return { home, work, usualProviders };
}

module.exports = { deriveAnchors, WORK_MIN_OCCURRENCES, USUAL_MIN_VISITS };
