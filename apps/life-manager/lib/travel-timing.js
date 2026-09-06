"use strict";

const MINUTE_MS = 60 * 1000;

function toMs(value) {
  if (value instanceof Date) {
    const ms = value.getTime();
    return Number.isFinite(ms) ? ms : null;
  }
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim()) {
    const ms = Date.parse(value);
    return Number.isFinite(ms) ? ms : null;
  }
  return null;
}

function routeDurationSeconds(route) {
  if (!route || typeof route !== "object") return null;
  const seconds = Number(route.durationSeconds ?? route.durationSecs ?? route.duration_seconds);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function nonNegativeMinutes(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

// The shared physical-event authority: door departure is the Calendar event start minus the exact
// structured route duration minus one explicit leave buffer. The provider route already owns access
// and egress semantics; callers must not round to minutes before this calculation or add the buffer
// again downstream.
function computeDoorDepartureMs(eventStart, route, { bufferMin = 5 } = {}) {
  const start = toMs(eventStart);
  const seconds = routeDurationSeconds(route);
  if (start === null || seconds === null) return null;
  return start - seconds * 1000 - nonNegativeMinutes(bufferMin, 5) * MINUTE_MS;
}

function computeT5ReminderMs(departure, { leadMin = 5 } = {}) {
  const departureMs = toMs(departure);
  if (departureMs === null) return null;
  return departureMs - nonNegativeMinutes(leadMin, 5) * MINUTE_MS;
}

module.exports = {
  MINUTE_MS,
  toMs,
  routeDurationSeconds,
  computeDoorDepartureMs,
  computeT5ReminderMs,
};
