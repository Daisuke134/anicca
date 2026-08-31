"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { isVerifiedEventProviderRegistry } = require("./event-provider-registry.js");

const CURSORS = new WeakSet();
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const KEYS = [
  "schema_version", "registry_id", "date", "provider", "candidate_index", "generation", "observed_at",
];

function invalid() { throw new Error("event provider cursor invalid"); }

function instant(value) {
  const text = String(value || "");
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== text) invalid();
  return milliseconds;
}

function validDate(value) {
  if (!DATE.test(String(value || ""))) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().startsWith(`${value}T`);
}

function checked(value, registry, requireProvenance = false) {
  if (
    !isVerifiedEventProviderRegistry(registry)
    || !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).length !== KEYS.length
    || !KEYS.every((key, index) => Object.keys(value)[index] === key)
    || value.schema_version !== 1
    || value.registry_id !== registry.registry_id
    || !validDate(value.date)
    || !registry.provider_order.includes(value.provider)
    || !Number.isSafeInteger(value.candidate_index) || value.candidate_index < 0
    || !Number.isSafeInteger(value.generation) || value.generation < 1
  ) invalid();
  instant(value.observed_at);
  if (requireProvenance && !CURSORS.has(value)) invalid();
  return value;
}

function verified(value) {
  const result = Object.freeze(value);
  CURSORS.add(result);
  return result;
}

function createEventProviderCursor(input = {}) {
  if (!isVerifiedEventProviderRegistry(input.registry) || !validDate(input.date)) invalid();
  instant(input.observedAt);
  return verified({
    schema_version: 1,
    registry_id: input.registry.registry_id,
    date: input.date,
    provider: input.registry.provider_order[0],
    candidate_index: 0,
    generation: 1,
    observed_at: input.observedAt,
  });
}

function advanceEventProviderCursor(input = {}) {
  const cursor = checked(input.cursor, input.registry, true);
  const observedAt = String(input.observedAt || "");
  if (instant(observedAt) <= instant(cursor.observed_at)) invalid();
  let provider = cursor.provider;
  let candidateIndex = cursor.candidate_index;
  if (input.transition === "known_no_effect") candidateIndex += 1;
  else if (input.transition === "provider_exhausted") {
    const index = input.registry.provider_order.indexOf(provider);
    if (index < 0 || index + 1 >= input.registry.provider_order.length) invalid();
    provider = input.registry.provider_order[index + 1];
    candidateIndex = 0;
  } else invalid();
  return verified({
    schema_version: 1,
    registry_id: cursor.registry_id,
    date: cursor.date,
    provider,
    candidate_index: candidateIndex,
    generation: cursor.generation + 1,
    observed_at: observedAt,
  });
}

function createEventProviderCursorStore(options = {}) {
  if (!isVerifiedEventProviderRegistry(options.registry)) invalid();
  const target = path.resolve(String(options.path || ""));
  if (!path.isAbsolute(target) || path.basename(target) !== "provider-cursor.json") invalid();
  return Object.freeze({
    read() {
      let raw;
      try { raw = JSON.parse(fs.readFileSync(target, "utf8")); } catch { invalid(); }
      checked(raw, options.registry);
      return verified(Object.freeze(raw));
    },
    write(cursor) {
      checked(cursor, options.registry, true);
      fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 });
      const temporary = `${target}.tmp-${process.pid}`;
      try {
        const descriptor = fs.openSync(temporary, "wx", 0o600);
        try {
          fs.writeFileSync(descriptor, `${JSON.stringify(cursor, null, 2)}\n`, "utf8");
          fs.fsyncSync(descriptor);
        } finally { fs.closeSync(descriptor); }
        fs.renameSync(temporary, target);
        fs.chmodSync(target, 0o600);
      } finally {
        try { fs.unlinkSync(temporary); } catch (error) { if (error.code !== "ENOENT") throw error; }
      }
      return cursor;
    },
  });
}

module.exports = {
  advanceEventProviderCursor,
  createEventProviderCursor,
  createEventProviderCursorStore,
};
