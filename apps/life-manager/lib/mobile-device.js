"use strict";

const { MobileError, nowIso, normalizeLocale, safeTimeZone } = require("./mobile-utils.js");

const APNS_TOKEN_RE = /^[0-9a-f]{64}$/iu;

function validateDevice(input = {}) {
  const token = String(input.token || input.deviceToken || "").trim().toLowerCase();
  if (!APNS_TOKEN_RE.test(token)) throw new MobileError("device_token_invalid", "The APNs device token is invalid.");
  const environment = String(input.environment || "").toLowerCase();
  if (environment !== "production" && environment !== "development") throw new MobileError("device_environment_invalid", "The APNs environment is invalid.");
  const locale = normalizeLocale(input.locale || "en");
  const timezone = safeTimeZone(input.timezone || "UTC");
  return { token, environment, locale, timezone };
}

async function upsertMobileDevice(scope, input, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const value = validateDevice(input);
  if (!deps.store || typeof deps.store.upsertDevice !== "function") throw new MobileError("device_store_unavailable", "Device storage is unavailable.", 503, true);
  const seenAt = nowIso(deps);
  const stored = await deps.store.upsertDevice(scope, { ...value, last_seen_at: seenAt });
  return {
    deviceId: stored.deviceId || stored.device_id || `device:v1:${scope.uid}:${value.token.slice(-8)}`,
    token: value.token, environment: value.environment, locale: value.locale, timezone: value.timezone,
    lastSeenAt: stored.lastSeenAt || stored.last_seen_at || seenAt,
  };
}

async function removeMobileDevice(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const value = validateDevice({ ...input, environment: input.environment || "production", locale: input.locale || "en", timezone: input.timezone || "UTC" });
  if (!deps.store || typeof deps.store.deleteDevice !== "function") throw new MobileError("device_store_unavailable", "Device storage is unavailable.", 503, true);
  await deps.store.deleteDevice(scope, value.token);
  return { deleted: true };
}

module.exports = { APNS_TOKEN_RE, validateDevice, upsertMobileDevice, removeMobileDevice };
