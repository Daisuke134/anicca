"use strict";
// 11a PHY-a — unmet-care detection (§9.1 PHYSICAL organ).
// Detects "hasn't been to the dentist / barber / …" from the user's OWN
// calendar history and intent graph. Two hard rules from the spec:
// no fixed cycle is imposed on anyone (a cadence exists only when the user's
// own history shows one — zero or one past visit flags nothing), and no
// medical diagnosis is ever produced (output is visit-gap observations only;
// the closed output schema has no field a diagnosis could live in).

const { buildGraph, effectiveEntries } = require("./intent-graph.js");

const OVERDUE_FACTOR = 1.5;
const GOAL_UNMET_MIN_DAYS = 30;
const DAY_MS = 86400000;

// CADENCE-1 (§10 row CADENCE-1) — the cadence-stability guard.
// The first production scan (2026-07-26) read six real clinic visits with gaps of
// 3.2 / 5.7 / 8.5 / 47 / 419 days and reported "personal_interval_days=9, overdue_days=50".
// Every number was correct; the CLAIM was not. Three visits inside ten weeks of 2025, fourteen
// months of silence, then two visits in one week of 2026 is a burst, and a median over a burst is
// not a cadence — so "50 days overdue against a 9-day cycle" compares a real elapsed time against
// a quantity that does not describe the user's behaviour. Booking off it would have been the true
// false positive. A gap set therefore earns the word "cadence" only when the gaps are mutually
// consistent enough that "overdue vs cadence" is a meaningful comparison at all.
const MIN_CADENCE_GAPS = 3; // ≥3 gaps = ≥4 visits; two gaps cannot show consistency
const MAD_MAX_RATIO = 0.5; // median absolute deviation ≤ half the median gap
const GAP_BAND_LOW = 0.4; // …or every gap inside [0.4×m, 2.5×m], which tolerates a
const GAP_BAND_HIGH = 2.5; //    wide-but-bounded rhythm the MAD clause would reject

const INPUT_KEYS = Object.freeze(["nowMs", "visits", "intents"]);
const VISIT_KEYS = Object.freeze(["startMs", "careType"]);
const CANDIDATE_KEYS = Object.freeze([
  "careType", "reason", "lastVisitMs", "personalIntervalDays", "overdueDays",
  "decision", "decisionReason",
]);

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("input must be an object");
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Array.isArray(input.visits)) throw new Error("visits must be an array");
  for (const visit of input.visits) {
    if (!visit || typeof visit !== "object") throw new Error("visit must be an object");
    for (const key of Object.keys(visit)) {
      if (!VISIT_KEYS.includes(key)) throw new Error(`unknown key: visit.${key}`);
    }
    if (!Number.isFinite(visit.startMs)) throw new Error("visit.startMs must be a finite number");
    if (!nonEmptyString(visit.careType)) throw new Error("visit.careType must be a non-empty string");
  }
  if (!Array.isArray(input.intents)) throw new Error("intents must be an array");
  return input;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// Is this gap set a cadence, or just a set of gaps? Pure arithmetic over inter-visit gaps in ms;
// no clock, no I/O, no care-type knowledge — a barber and a clinic are judged by the same rule.
// Returns "act" (the gaps really do describe a rhythm) or "observe" with the reason it does not.
// "observe" is NOT a rejection of the observation: the detection is still recorded, it just may
// not be acted upon. The two clauses are deliberately a disjunction — MAD is the robust
// dispersion measure, and the band clause admits a wide-but-bounded rhythm the MAD would reject.
function judgeCadenceStability(gaps) {
  if (!Array.isArray(gaps) || gaps.length < MIN_CADENCE_GAPS) {
    return { decision: "observe", reason: "insufficient-gaps" };
  }
  const m = median(gaps);
  if (!(m > 0)) return { decision: "observe", reason: "cadence-unstable" };
  const mad = median(gaps.map((gap) => Math.abs(gap - m)));
  const dispersionOk = mad <= MAD_MAX_RATIO * m;
  const bandOk = gaps.every((gap) => gap >= GAP_BAND_LOW * m && gap <= GAP_BAND_HIGH * m);
  if (dispersionOk || bandOk) return { decision: "act", reason: null };
  return { decision: "observe", reason: "cadence-unstable" };
}

// careType linkage to intents rides on the statement carrying "care:<type>"
// so linkage stays deterministic data, not text inference.
function careTag(entry) {
  const match = /care:([a-z0-9_-]+)/.exec(entry.statement);
  return match ? match[1] : null;
}

function detectUnmetCare(input) {
  validateInput(input);
  const { nowMs, visits } = input;
  const active = effectiveEntries(buildGraph(input.intents), nowMs);
  const prohibited = new Set(active.filter((e) => e.kind === "prohibition").map(careTag).filter(Boolean));

  const byType = new Map();
  for (const visit of visits.filter((v) => v.startMs <= nowMs)) {
    if (!byType.has(visit.careType)) byType.set(visit.careType, []);
    byType.get(visit.careType).push(visit.startMs);
  }

  const candidates = [];

  // Personal-cadence detection: the user's own repeat pattern, never a global cycle.
  for (const careType of [...byType.keys()].sort()) {
    if (prohibited.has(careType)) continue;
    const times = byType.get(careType).sort((a, b) => a - b);
    if (times.length < 2) continue;
    const gaps = times.slice(1).map((t, i) => t - times[i]);
    const personalInterval = median(gaps);
    const last = times[times.length - 1];
    const sinceLast = nowMs - last;
    if (sinceLast > OVERDUE_FACTOR * personalInterval) {
      // CADENCE-1: an overdue-looking gap is still recorded when the underlying gaps are not a
      // cadence — silently dropping it would make the append-only scan log lie about what was
      // seen — but it is marked "observe" so no downstream step may act on it.
      const stability = judgeCadenceStability(gaps);
      candidates.push({
        careType, reason: "personal-cadence-overdue", lastVisitMs: last,
        personalIntervalDays: Math.round(personalInterval / DAY_MS),
        overdueDays: Math.round((sinceLast - personalInterval) / DAY_MS),
        decision: stability.decision,
        decisionReason: stability.reason,
      });
    }
  }

  // Explicit-goal detection: the user said they want this care and no visit
  // has happened since — flag once enough time has passed to matter.
  for (const goal of active.filter((e) => e.kind === "explicit_goal")) {
    const careType = careTag(goal);
    if (!careType || prohibited.has(careType)) continue;
    if (candidates.some((c) => c.careType === careType)) continue;
    const goalMs = Date.parse(goal.provenance.observedAt);
    const visitedSince = (byType.get(careType) || []).some((t) => t > goalMs);
    if (!visitedSince && nowMs - goalMs > GOAL_UNMET_MIN_DAYS * DAY_MS) {
      const times = (byType.get(careType) || []).sort((a, b) => a - b);
      candidates.push({
        careType, reason: "explicit-goal-unmet",
        lastVisitMs: times.length ? times[times.length - 1] : null,
        personalIntervalDays: null,
        overdueDays: Math.round((nowMs - goalMs) / DAY_MS),
        // No cadence is claimed here and none is needed: the user explicitly asked for this care,
        // which is a stronger mandate than any inferred rhythm. The guard has nothing to judge.
        decision: "act",
        decisionReason: null,
      });
    }
  }

  for (const candidate of candidates) {
    for (const key of Object.keys(candidate)) {
      if (!CANDIDATE_KEYS.includes(key)) throw new Error(`unknown key: candidate.${key}`);
    }
  }
  return { candidates };
}

module.exports = {
  validateInput, detectUnmetCare, judgeCadenceStability,
  OVERDUE_FACTOR, GOAL_UNMET_MIN_DAYS,
  MIN_CADENCE_GAPS, MAD_MAX_RATIO, GAP_BAND_LOW, GAP_BAND_HIGH,
};
