"use strict";

const fs = require("node:fs");
const path = require("node:path");

const FORBIDDEN_KEY = /(?:password|secret|cookie|session|api[_-]?key|access[_-]?token|private[_-]?key)/i;

function unavailable() { throw new Error("Connector user profile unavailable"); }

function inspect(value, depth = 0) {
  if (depth > 12) unavailable();
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) unavailable();
    return value;
  }
  if (typeof value === "string") {
    if (value.length > 8_000 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) unavailable();
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length > 200) unavailable();
    return Object.freeze(value.map((item) => inspect(item, depth + 1)));
  }
  if (!value || typeof value !== "object") unavailable();
  const entries = Object.entries(value);
  if (entries.length > 200 || entries.some(([key]) => FORBIDDEN_KEY.test(key))) unavailable();
  return Object.freeze(Object.fromEntries(entries.map(([key, item]) => [key, inspect(item, depth + 1)])));
}

function readConnectorUserProfile(input = {}) {
  const file = path.resolve(String(input.path == null ? "" : input.path));
  if (!path.isAbsolute(file) || file === path.parse(file).root) unavailable();
  let parsed;
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < 2 || stat.size > 262_144 || (stat.mode & 0o777) !== 0o600) unavailable();
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch { unavailable(); }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)
    || !parsed.candidate || typeof parsed.candidate !== "object" || Array.isArray(parsed.candidate)) unavailable();
  return inspect(parsed);
}

module.exports = { readConnectorUserProfile };
