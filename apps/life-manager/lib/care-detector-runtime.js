"use strict";

const { detectUnmetCare } = require("./care-detector");

function eventStartMs(event) {
  const raw = event?.start?.dateTime || event?.start?.date || event?.start;
  const value = Date.parse(raw);
  return Number.isFinite(value) ? value : null;
}

function detectCalendarCare(input) {
  const nowMs = input.nowMs;
  const seen = new Set();
  const visits = [];
  const idsByType = new Map();

  for (const source of Array.isArray(input.sources) ? input.sources : []) {
    if (!source || typeof source.careType !== "string" || !source.careType.trim()) continue;
    for (const event of Array.isArray(source.events) ? source.events : []) {
      const id = event && typeof event.id === "string" ? event.id.trim() : "";
      const startMs = eventStartMs(event);
      const key = `${source.careType}:${id}`;
      if (!id || startMs === null || startMs > nowMs || seen.has(key)) continue;
      seen.add(key);
      visits.push({ careType: source.careType, startMs });
      if (!idsByType.has(source.careType)) idsByType.set(source.careType, []);
      idsByType.get(source.careType).push(id);
    }
  }

  const detected = detectUnmetCare({
    nowMs,
    visits,
    intents: Array.isArray(input.intents) ? input.intents : [],
  });
  return {
    schema_version: 1,
    real_event_count: visits.length,
    // observe_only / decision_reason carry the CADENCE-1 verdict into the persisted scan row:
    // observe_only:true means "this was really seen, and it is not something to act on" (the gaps
    // are not a cadence, so overdue_days is not a meaningful debt). The row stays honest; the 11b
    // chain in care-daily-runtime.js runs only for observe_only:false detections.
    candidates: detected.candidates.map((candidate) => ({
      care_type: candidate.careType,
      reason: candidate.reason,
      personal_interval_days: candidate.personalIntervalDays,
      overdue_days: candidate.overdueDays,
      observe_only: candidate.decision === "observe",
      decision_reason: candidate.decisionReason ?? null,
      source_provider_ids: [...(idsByType.get(candidate.careType) || [])].sort(),
    })),
  };
}

module.exports = { detectCalendarCare };
