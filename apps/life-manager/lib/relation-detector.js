"use strict";

const {
  judgeCadenceStability,
  OVERDUE_FACTOR,
} = require("./care-detector.js");

const DAY_MS = 86400000;
const INPUT_KEYS = Object.freeze(["nowMs", "interactions"]);
const INTERACTION_KEYS = Object.freeze([
  "interactionId",
  "personKey",
  "label",
  "startMs",
  "source",
]);
const SOURCES = new Set([
  "calendar_1to1",
  "whatsapp_chat",
  "telegram_user_session",
  "agent_call",
]);
const CANDIDATE_KEYS = Object.freeze([
  "personKey",
  "label",
  "source",
  "lastInteractionMs",
  "personalIntervalDays",
  "daysSince",
  "overdueDays",
  "overdueRatio",
  "decision",
  "decisionReason",
]);

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("input must be an object");
  }
  for (const key of Object.keys(input)) {
    if (!INPUT_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!Number.isFinite(input.nowMs)) throw new Error("nowMs must be a finite number");
  if (!Array.isArray(input.interactions)) throw new Error("interactions must be an array");

  for (const interaction of input.interactions) {
    if (!interaction || typeof interaction !== "object" || Array.isArray(interaction)) {
      throw new Error("interaction must be an object");
    }
    for (const key of Object.keys(interaction)) {
      if (!INTERACTION_KEYS.includes(key)) throw new Error(`unknown key: interaction.${key}`);
    }
    if (!nonEmptyString(interaction.interactionId)) {
      throw new Error("interaction.interactionId must be a non-empty string");
    }
    if (!nonEmptyString(interaction.personKey)) {
      throw new Error("interaction.personKey must be a non-empty string");
    }
    if (!nonEmptyString(interaction.label)) {
      throw new Error("interaction.label must be a non-empty string");
    }
    if (!Number.isFinite(interaction.startMs) || interaction.startMs > input.nowMs) {
      throw new Error("interaction.startMs must be a finite past timestamp");
    }
    if (!SOURCES.has(interaction.source)) {
      throw new Error("interaction.source is unsupported");
    }
  }
  return input;
}

function detectRelationCadence(input) {
  validateInput(input);
  const { nowMs } = input;
  const seen = new Set();
  const unique = [];
  for (const interaction of input.interactions) {
    if (seen.has(interaction.interactionId)) continue;
    seen.add(interaction.interactionId);
    unique.push(interaction);
  }

  const byPerson = new Map();
  for (const interaction of unique) {
    if (!byPerson.has(interaction.personKey)) byPerson.set(interaction.personKey, []);
    byPerson.get(interaction.personKey).push(interaction);
  }

  const candidates = [];
  for (const personKey of [...byPerson.keys()].sort()) {
    const rows = byPerson.get(personKey).sort((a, b) => a.startMs - b.startMs);
    if (rows.length < 3) continue;
    const times = rows.map((row) => row.startMs);
    const gaps = times.slice(1).map((time, index) => time - times[index]);
    const personalInterval = median(gaps);
    const last = rows[rows.length - 1];
    const sinceLast = nowMs - last.startMs;
    if (!(personalInterval > 0) || sinceLast <= OVERDUE_FACTOR * personalInterval) continue;

    const stability = judgeCadenceStability(gaps);
    const candidate = {
      personKey,
      label: last.label,
      source: last.source,
      lastInteractionMs: last.startMs,
      personalIntervalDays: Math.round(personalInterval / DAY_MS),
      daysSince: Math.round(sinceLast / DAY_MS),
      overdueDays: Math.round((sinceLast - personalInterval) / DAY_MS),
      overdueRatio: Number((sinceLast / personalInterval).toFixed(2)),
      decision: stability.decision,
      decisionReason: stability.reason,
    };
    for (const key of Object.keys(candidate)) {
      if (!CANDIDATE_KEYS.includes(key)) throw new Error(`unknown key: candidate.${key}`);
    }
    candidates.push(candidate);
  }

  candidates.sort((a, b) =>
    b.overdueRatio - a.overdueRatio || a.personKey.localeCompare(b.personKey));
  return { interactionCount: unique.length, candidates };
}

module.exports = {
  detectRelationCadence,
  validateInput,
  DAY_MS,
};
