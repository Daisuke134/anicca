"use strict";

const fs = require("node:fs");
const path = require("node:path");

const VERIFIED = new WeakSet();
const KEYS = Object.freeze([
  "browser_profile_ref", "calendar_ref", "goals", "identity_ref", "preferences",
  "schema_version", "spend_policy", "tenant_id", "timezone",
]);
const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const SECRET_LIKE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b(?:password|cookie|guest[_ -]?key|api[_ -]?key|access[_ -]?token|secret)\b/i;

function unavailable() { throw new Error("Connector profile unavailable"); }

function text(value, max) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!result || result.length > max || /[\x00-\x1f\x7f]/.test(result) || SECRET_LIKE.test(result)) unavailable();
  return result;
}

function exactReference(value, pattern) {
  const result = String(value == null ? "" : value).trim();
  if (!pattern.test(result)) unavailable();
  return result;
}

function readConnectorProfile(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  const file = path.resolve(String(input.path == null ? "" : input.path));
  if (!TENANT.test(tenantId) || !path.isAbsolute(file) || file === path.parse(file).root) unavailable();
  let parsed;
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < 2 || stat.size > 16_384) unavailable();
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch { unavailable(); }
  if (
    !parsed || typeof parsed !== "object" || Array.isArray(parsed)
    || Object.keys(parsed).sort().join(",") !== [...KEYS].sort().join(",")
    || parsed.schema_version !== 1
    || parsed.tenant_id !== tenantId
    || !parsed.spend_policy || typeof parsed.spend_policy !== "object"
    || Array.isArray(parsed.spend_policy)
    || Object.keys(parsed.spend_policy).join(",") !== "limits"
    || !Array.isArray(parsed.spend_policy.limits)
    || parsed.spend_policy.limits.length !== 0
  ) unavailable();
  const timezone = String(parsed.timezone == null ? "" : parsed.timezone).trim();
  try { new Intl.DateTimeFormat("en", { timeZone: timezone }).format(new Date(0)); }
  catch { unavailable(); }
  const profile = Object.freeze({
    schema_version: 1,
    tenant_id: tenantId,
    timezone,
    preferences: text(parsed.preferences, 2_000),
    goals: text(parsed.goals, 4_000),
    spend_policy: Object.freeze({ limits: Object.freeze([]) }),
    identity_ref: exactReference(parsed.identity_ref, /^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i),
    browser_profile_ref: exactReference(parsed.browser_profile_ref, /^browser-profile:\/\/cloakbrowser\/[a-z0-9._-]+$/i),
    calendar_ref: exactReference(parsed.calendar_ref, /^calendar:\/\/google\/[a-z0-9._-]+$/i),
  });
  VERIFIED.add(profile);
  return profile;
}

function isVerifiedConnectorProfile(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = { isVerifiedConnectorProfile, readConnectorProfile };

