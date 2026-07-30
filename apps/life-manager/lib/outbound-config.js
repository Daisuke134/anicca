// lib/outbound-config.js — pack config loading + hand-written schema validation.
//
// One engine, three config packs (spec §1). The validator is written by hand on purpose: adding
// a schema library for five fields would be a new dependency for no gain, and a hand-written
// check names the offending field in its error, which is what a 07:30 launchd failure needs.
//
// The denylist is the ONE deterministic part of QUALIFY (spec §3.1: "denylist のみ決定的").
// Everything else about whether to apply is the model's judgment, never a regex.
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const PACKS = Object.freeze(["events", "funders", "jobs"]);

// apps/life-manager/lib -> apps/life-manager -> apps -> repo root
const REPO_ROOT = path.join(__dirname, "..", "..", "..");
const PACK_DIR = path.join(REPO_ROOT, "skills", "life-manager", "outbound");

function assertKnownPack(pack) {
  const name = String(pack == null ? "" : pack);
  if (!PACKS.includes(name)) {
    throw new Error(`outbound pack must be one of ${PACKS.join(", ")}, got ${JSON.stringify(name)}`);
  }
  return name;
}

function packDir(pack) {
  return path.join(PACK_DIR, assertKnownPack(pack));
}

function packConfigPath(pack) {
  return path.join(packDir(pack), "config.json");
}

function isStringArray(value, { allowEmpty }) {
  return Array.isArray(value)
    && (allowEmpty || value.length > 0)
    && value.every((entry) => typeof entry === "string" && entry.length > 0);
}

/**
 * Validate a pack config object. Returns a frozen copy; throws with the field name on any breach.
 */
function validatePackConfig(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("outbound pack config must be a JSON object");
  }
  for (const field of ["pack", "enabled", "daily_cap", "denylist", "segments"]) {
    if (!Object.prototype.hasOwnProperty.call(raw, field)) {
      throw new Error(`outbound pack config is missing ${field}`);
    }
  }
  assertKnownPack(raw.pack);
  if (typeof raw.enabled !== "boolean") {
    throw new Error("outbound pack config enabled must be a boolean");
  }
  if (!Number.isInteger(raw.daily_cap) || raw.daily_cap < 1) {
    throw new Error("outbound pack config daily_cap must be a positive integer");
  }
  if (!isStringArray(raw.denylist, { allowEmpty: true })) {
    throw new Error("outbound pack config denylist must be an array of strings");
  }
  if (!isStringArray(raw.segments, { allowEmpty: false })) {
    throw new Error("outbound pack config segments must be a non-empty array of strings");
  }
  return Object.freeze({
    ...raw,
    denylist: Object.freeze([...raw.denylist]),
    segments: Object.freeze([...raw.segments]),
    ...(Array.isArray(raw.sources) ? { sources: Object.freeze([...raw.sources]) } : {}),
  });
}

function loadPackConfig(pack, opts = {}) {
  const file = opts.configPath || packConfigPath(pack);
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    if (error && error.code === "ENOENT") {
      throw new Error(`outbound pack config not found at ${file}`);
    }
    if (error instanceof SyntaxError) {
      throw new Error(`outbound pack config at ${file} is not valid JSON: ${error.message}`);
    }
    throw error;
  }
  return validatePackConfig(raw);
}

function candidateText(candidate) {
  if (typeof candidate === "string") return candidate;
  if (!candidate || typeof candidate !== "object") return "";
  return [candidate.name, candidate.company, candidate.organizer, candidate.title, candidate.url]
    .filter((part) => typeof part === "string")
    .join(" ");
}

/**
 * @returns {string|null} the denylist entry that blocked the candidate, or null if it passes.
 */
function isDenied(config, candidate) {
  const haystack = candidateText(candidate).toLowerCase();
  if (!haystack) return null;
  for (const needle of (config && config.denylist) || []) {
    if (haystack.includes(String(needle).toLowerCase())) return needle;
  }
  return null;
}

module.exports = {
  PACKS,
  PACK_DIR,
  packDir,
  packConfigPath,
  validatePackConfig,
  loadPackConfig,
  isDenied,
};
