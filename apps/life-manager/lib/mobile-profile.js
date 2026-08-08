"use strict";

const { MobileError, normalizeLocale, safeTimeZone } = require("./mobile-utils.js");

const E164_RE = /^\+[1-9]\d{7,14}$/u;

function isValidE164(value) {
  return typeof value === "string" && E164_RE.test(value);
}

function text(value, fieldName, max = 500) {
  if (typeof value !== "string") throw new MobileError("invalid_profile", `${fieldName} must be text.`);
  const result = value.trim();
  if (!result || result.length > max || /[\x00-\x1f\x7f]/u.test(result)) throw new MobileError("invalid_profile", `${fieldName} is invalid.`);
  return result;
}

function validateMobileProfilePatch(body = {}, existing = {}) {
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new MobileError("invalid_profile", "Profile data is invalid.");
  const allowed = new Set(["name", "home", "productLocale", "phone", "callsEnabled", "callLanguage", "timezone"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) throw new MobileError("unknown_profile_field", `Profile field ${key} is not allowed.`);
  const patch = {};
  if (Object.hasOwn(body, "name")) patch.name = body.name == null ? null : text(body.name, "name", 120);
  if (Object.hasOwn(body, "home")) patch.home = body.home == null ? null : text(body.home, "home", 500);
  if (Object.hasOwn(body, "productLocale")) patch.productLocale = normalizeLocale(body.productLocale);
  if (Object.hasOwn(body, "phone")) {
    if (body.phone !== null && !isValidE164(body.phone)) throw new MobileError("invalid_phone", "Use an E.164 phone number.");
    patch.phone = body.phone;
  }
  if (Object.hasOwn(body, "callsEnabled")) {
    if (typeof body.callsEnabled !== "boolean") throw new MobileError("invalid_calls_enabled", "Call enablement must be explicit.");
    patch.callsEnabled = body.callsEnabled;
  }
  if (Object.hasOwn(body, "callLanguage")) {
    if (body.callLanguage !== null) patch.callLanguage = normalizeLocale(body.callLanguage);
    else patch.callLanguage = null;
  }
  if (Object.hasOwn(body, "timezone")) patch.timezone = safeTimeZone(body.timezone);

  if (patch.phone === null) {
    patch.callsEnabled = false;
    if (Object.hasOwn(body, "callLanguage")) patch.callLanguage = null;
  }
  const existingPhone = existing && (existing.phone || existing.phone_number);
  const effectivePhone = patch.phone !== undefined ? patch.phone : existingPhone;
  if (patch.callsEnabled === true && !effectivePhone) throw new MobileError("call_language_required", "Add a phone number before enabling calls.");
  const existingCallsEnabled = existing && (existing.callsEnabled === true || existing.calls_enabled === true);
  const effectiveCallsEnabled = patch.callsEnabled === undefined ? existingCallsEnabled : patch.callsEnabled;
  if (!effectiveCallsEnabled && Object.hasOwn(patch, "callLanguage") && patch.callLanguage !== null) {
    throw new MobileError("calls_disabled", "Call language can be changed after calls are enabled.");
  }
  if (patch.callsEnabled === true && !Object.hasOwn(patch, "callLanguage")) {
    patch.callLanguage = patch.productLocale || existing.callLanguage || existing.call_language || existing.productLocale || existing.product_locale || "en";
  }
  return patch;
}

function outputProfile(row, patch) {
  const source = { ...(row || {}), ...(patch || {}) };
  const callsEnabled = source.callsEnabled !== undefined ? source.callsEnabled : source.calls_enabled;
  const callLanguage = source.callLanguage !== undefined ? source.callLanguage : source.call_language;
  return {
    name: source.name === undefined ? null : source.name,
    home: source.home !== undefined ? source.home : (source.home_address === undefined ? null : source.home_address),
    productLocale: source.productLocale || source.product_locale || "en",
    phone: source.phone === undefined ? null : source.phone,
    callsEnabled: callsEnabled === true,
    callLanguage: callsEnabled === true ? (callLanguage || null) : null,
  };
}

async function patchMobileProfile(scope, body, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const store = deps.store;
  if (!store || typeof store.patchUser !== "function") throw new MobileError("profile_store_unavailable", "Profile storage is unavailable.", 503, true);
  const needsExisting = body && (body.callsEnabled === true || Object.hasOwn(body, "callLanguage"));
  const existing = needsExisting && typeof store.readUser === "function" ? await store.readUser(scope) : null;
  const patch = validateMobileProfilePatch(body, existing || {});
  if (patch.phone === null && !Object.hasOwn(patch, "callLanguage")) patch.callLanguage = null;
  const stored = await store.patchUser(scope, {
    ...(patch.name !== undefined ? { name: patch.name } : {}),
    ...(patch.home !== undefined ? { home_address: patch.home } : {}),
    ...(patch.productLocale !== undefined ? { product_locale: patch.productLocale } : {}),
    ...(patch.phone !== undefined ? { phone: patch.phone } : {}),
    ...(patch.callsEnabled !== undefined ? { calls_enabled: patch.callsEnabled } : {}),
    ...(patch.callLanguage !== undefined ? { call_language: patch.callLanguage } : {}),
    ...(patch.timezone !== undefined ? { time_zone: patch.timezone } : {}),
  });
  return outputProfile({ ...(existing || {}), ...(stored || {}) }, patch);
}

module.exports = { E164_RE, isValidE164, validateMobileProfilePatch, patchMobileProfile, outputProfile };
