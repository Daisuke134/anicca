"use strict";

const crypto = require("node:crypto");

const MIN_DURATION_MS = 10 * 60 * 1000;
const MAX_DURATION_MS = 6 * 60 * 60 * 1000;

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function personKeyForEmail(email, secret) {
  if (!nonEmpty(secret)) throw new Error("relations HMAC secret is required");
  if (!nonEmpty(email)) throw new Error("attendee email is required");
  const digest = crypto
    .createHmac("sha256", secret)
    .update(email.trim().toLowerCase())
    .digest("hex")
    .slice(0, 32);
  return `rel_${digest}`;
}

function safeDisplayName(value) {
  if (!nonEmpty(value)) return null;
  const label = value.trim().replace(/\s+/g, " ");
  if (label.length > 80) return null;
  if (/@|https?:\/\/|(?:\+?\d[\d ()-]{7,}\d)/i.test(label)) return null;
  return label;
}

function externalHumans(attendees) {
  return (Array.isArray(attendees) ? attendees : []).filter((attendee) =>
    attendee &&
    typeof attendee === "object" &&
    attendee.self !== true &&
    attendee.resource !== true &&
    attendee.responseStatus !== "declined");
}

function extractCalendarInteractions(events, opts = {}) {
  if (!nonEmpty(opts.secret)) throw new Error("relations HMAC secret is required");
  if (!Array.isArray(events)) throw new Error("events must be an array");

  const interactions = [];
  for (const event of events) {
    if (!event || typeof event !== "object") continue;
    if (!nonEmpty(event.id) || !Number.isFinite(event.startMs) || !Number.isFinite(event.endMs)) continue;
    const duration = event.endMs - event.startMs;
    if (duration < MIN_DURATION_MS || duration > MAX_DURATION_MS) continue;

    const people = externalHumans(event.attendees);
    if (people.length !== 1) continue;
    const person = people[0];
    const label = safeDisplayName(person.displayName);
    if (!label || !nonEmpty(person.email)) continue;

    interactions.push({
      interactionId: event.id,
      personKey: personKeyForEmail(person.email, opts.secret),
      label,
      startMs: event.startMs,
      source: "calendar_1to1",
    });
  }
  return interactions;
}

module.exports = {
  extractCalendarInteractions,
  personKeyForEmail,
  safeDisplayName,
  MIN_DURATION_MS,
  MAX_DURATION_MS,
};
