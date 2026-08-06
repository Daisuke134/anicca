"use strict";

const EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;
const OUTCOMES = new Set([
  "verified_success",
  "known_no_effect",
  "unknown_effect",
  "recovery_required",
]);

function invalid() {
  throw new Error("Connector candidate suppression invalid");
}

function exactInstant(value) {
  const text = String(value || "").trim();
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== text) invalid();
  return milliseconds;
}

function checkedAttempt(attempt) {
  if (
    !attempt || typeof attempt !== "object" || Array.isArray(attempt)
    || !EVENT_REF.test(String(attempt.event_ref || ""))
    || !OUTCOMES.has(attempt.outcome)
    || !/^[A-Za-z0-9_:-]{1,100}$/.test(String(attempt.safe_reason || ""))
    || !(attempt.retry_after === null || typeof attempt.retry_after === "string")
  ) invalid();
  const observedAt = exactInstant(attempt.observed_at);
  const retryAfter = attempt.retry_after === null ? null : exactInstant(attempt.retry_after);
  return { ...attempt, observedAt, retryAfter };
}

function latestCandidateAttempts(input = {}) {
  const now = exactInstant(input.now);
  if (!Array.isArray(input.attempts) || input.attempts.length > 10_000) invalid();
  const latest = new Map();
  for (const raw of input.attempts) {
    const attempt = checkedAttempt(raw);
    const previous = latest.get(attempt.event_ref);
    if (!previous || attempt.observedAt > previous.observedAt) latest.set(attempt.event_ref, attempt);
  }
  return Object.freeze({ now, latest });
}

function activeSuppressedEventRefs(input = {}) {
  const { now, latest } = latestCandidateAttempts(input);
  const suppressed = new Set();
  for (const attempt of latest.values()) {
    if (
      attempt.outcome === "known_no_effect"
      && (attempt.retryAfter === null || attempt.retryAfter > now)
    ) suppressed.add(attempt.event_ref);
  }
  return suppressed;
}

module.exports = { activeSuppressedEventRefs, latestCandidateAttempts };
