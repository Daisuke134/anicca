"use strict";

const ASSESSMENT_KEYS = Object.freeze(["event_ref", "priority_score", "reason", "signals"]);
const EVENT_REF = /^[a-z][a-z0-9+.-]*:\/\/event\/[A-Za-z0-9_-]+$/i;

function invalid(label) { throw new Error(`event candidate priority ${label} invalid`); }
function exactKeys(value, keys) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join(",") === [...keys].sort().join(",");
}

function validCandidate(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return false;
  if (!EVENT_REF.test(String(candidate.event_ref || ""))) return false;
  if (!String(candidate.title || "").trim() || !/^\d{4}-\d{2}-\d{2}$/.test(String(candidate.event_date || ""))) return false;
  try {
    const url = new URL(String(candidate.canonical_url || ""));
    return url.protocol === "https:" && !url.username && !url.password;
  } catch { return false; }
}

function rankEventCandidatesLosslessly(candidates, assessments) {
  if (!Array.isArray(candidates) || !Array.isArray(assessments) || candidates.some((row) => !validCandidate(row))) {
    invalid("input");
  }
  const candidateMap = new Map();
  for (const candidate of candidates) {
    if (candidateMap.has(candidate.event_ref)) invalid("duplicate candidate");
    candidateMap.set(candidate.event_ref, candidate);
  }
  const assessmentMap = new Map();
  for (const assessment of assessments) {
    if (!exactKeys(assessment, ASSESSMENT_KEYS)) invalid("assessment schema");
    const eventRef = String(assessment.event_ref || "");
    if (assessmentMap.has(eventRef)) invalid("duplicate assessment");
    if (!Number.isInteger(assessment.priority_score) || assessment.priority_score < 0 || assessment.priority_score > 100) invalid("assessment score");
    const reason = String(assessment.reason || "").trim();
    if (!reason || reason.length > 500) invalid("assessment reason");
    if (!Array.isArray(assessment.signals) || assessment.signals.length > 10
      || assessment.signals.some((signal) => !String(signal).trim() || String(signal).length > 80)) invalid("assessment signals");
    const signals = [...new Set(assessment.signals.map((signal) => String(signal).trim()))];
    if (signals.length !== assessment.signals.length) invalid("assessment signals");
    assessmentMap.set(eventRef, Object.freeze({
      priority_score: assessment.priority_score,
      signals: Object.freeze(signals),
      reason,
    }));
  }
  if (candidateMap.size !== assessmentMap.size
    || [...candidateMap.keys()].some((eventRef) => !assessmentMap.has(eventRef))) invalid("one-to-one assessment");
  const ranked = [...candidateMap.values()].map((candidate) => Object.freeze({
    ...candidate,
    ...assessmentMap.get(candidate.event_ref),
  })).sort((left, right) => right.priority_score - left.priority_score || left.event_ref.localeCompare(right.event_ref));
  return Object.freeze({
    schema_version: 1,
    policy: "priority_only_no_category_filter",
    input_count: candidates.length,
    output_count: ranked.length,
    dropped_count: candidates.length - ranked.length,
    ranked: Object.freeze(ranked),
  });
}

module.exports = { rankEventCandidatesLosslessly };
