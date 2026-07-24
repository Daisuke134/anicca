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

const INPUT_KEYS = Object.freeze(["nowMs", "visits", "intents"]);
const VISIT_KEYS = Object.freeze(["startMs", "careType"]);
const CANDIDATE_KEYS = Object.freeze([
  "careType", "reason", "lastVisitMs", "personalIntervalDays", "overdueDays",
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
      candidates.push({
        careType, reason: "personal-cadence-overdue", lastVisitMs: last,
        personalIntervalDays: Math.round(personalInterval / DAY_MS),
        overdueDays: Math.round((sinceLast - personalInterval) / DAY_MS),
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

module.exports = { validateInput, detectUnmetCare, OVERDUE_FACTOR, GOAL_UNMET_MIN_DAYS };
