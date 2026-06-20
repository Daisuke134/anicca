// lib/wake-filter.js — #69 wake/travel importance filter (kills routine spam) + leave-time anchor
// (never-late). PURE, unit-tested in wake-filter.test.js. Used by scheduler.js tick().
"use strict";

// Anicca's own inserted blocks are not real commitments — never wake someone for them.
function isHelperBlock(summary) {
  const s = summary || "";
  return s.startsWith("[Travel]") || s.includes("🚆 移動") || s.includes("[PENDING]") || s.includes("[APPLIED]");
}

const norm = (s) => (s || "").replace(/\s+/g, "").toLowerCase();

// Should we place a wake call for this event?
//   travel-only (default): only events you must TRAVEL to — a real location that isn't home. Routines
//     (no location, or at home) are skipped → no 27-calls-a-day spam. Home unknown → skip (can't judge;
//     the ask-loop resolves home first).
//   all-events: any timed non-helper event (opt-in to the original behavior).
// Helper blocks are never woken for under any policy.
function shouldWake(ev, home, policy = "travel-only") {
  if (!ev || isHelperBlock(ev.summary)) return false;
  if (policy === "all-events") return true;
  const loc = norm(ev.location);
  if (!loc) return false;            // no location → routine / phone task → no travel
  if (!norm(home)) return false;     // home unknown → can't tell travel vs at-home → skip
  return loc !== norm(home);         // travel only when the venue differs from home
}

// Leave-time anchor: if travel.js inserted a [Travel] block that ENDS exactly at this event's start,
// the user must LEAVE at that block's start — so wakes anchor there, not at event start (else a
// 30-min-travel event would be called only after the user already had to leave). No matching block →
// event start. Only [Travel] HELPER blocks count (a real back-to-back meeting is not a departure).
function departureMs(ev, allEvents) {
  if (!ev) return null;
  const start = ev.startMs;
  const block = (allEvents || []).find(
    (e) => e && isHelperBlock(e.summary) && Number.isFinite(e.endMs) && e.endMs === start && Number.isFinite(e.startMs)
  );
  return block ? block.startMs : start;
}

module.exports = { isHelperBlock, shouldWake, departureMs };
