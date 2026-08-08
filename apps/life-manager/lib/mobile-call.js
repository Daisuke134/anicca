"use strict";

const { MobileError, nowIso } = require("./mobile-utils.js");
const { isValidE164 } = require("./mobile-profile.js");

async function requestMobileCall(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  if (input.confirmed !== true) throw new MobileError("call_confirmation_required", "Confirm before placing the call.");
  if (!input.idempotencyKey) throw new MobileError("idempotency_required", "Idempotency-Key is required for this mutation.");
  const store = deps.store;
  if (!store || typeof store.readUser !== "function" || typeof store.claimCallAttempt !== "function") throw new MobileError("call_store_unavailable", "Call storage is unavailable.", 503, true);
  const user = await store.readUser(scope);
  const phone = user && user.phone;
  if (!phone) throw new MobileError("phone_required", "Add a phone number before placing a call.");
  if (!isValidE164(phone)) throw new MobileError("invalid_phone", "Use an E.164 phone number.");
  if (!(user.calls_enabled === true || user.callsEnabled === true)) throw new MobileError("calls_disabled", "Enable calls in Settings before placing a call.");
  const now = nowIso(deps);
  const claim = await store.claimCallAttempt(scope, { idempotencyKey: input.idempotencyKey, now });
  if (!claim || claim.rateLimited || claim.allowed === false) {
    throw new MobileError("call_rate_limited", "Calls are temporarily rate-limited.", 429, true, { reason: claim && claim.reason || "daily_limit" });
  }
  const attemptId = claim.attemptId || claim.attempt_id;
  const placeCall = deps.placeCall || require("./dial.js").placeCall;
  const callLanguage = user.call_language || user.callLanguage || user.product_locale || user.productLocale || scope.productLocale || "en";
  try {
    const receipt = await placeCall({
      to: phone, language: callLanguage, callLanguage,
      name: user.name || null,
      event: input.event || null, summary: input.summary || null, dateTime: input.dateTime || null, location: input.location || null,
    });
    if (!receipt || receipt.ok !== true) throw new MobileError("call_provider_failed", "The call could not be placed.", 502, true);
    if (typeof store.finishCallAttempt === "function") await store.finishCallAttempt(scope, { attemptId, status: "placed", providerReceipt: { ccid: receipt.ccid || null } });
    return { status: "placed", attemptId, callLanguage, providerReceipt: { ccid: receipt.ccid || null } };
  } catch (error) {
    if (typeof store.finishCallAttempt === "function") await store.finishCallAttempt(scope, { attemptId, status: "failed", error: error.code || "provider_failed" }).catch(() => {});
    if (error instanceof MobileError) throw error;
    throw new MobileError("call_provider_failed", "The call could not be placed.", 502, true);
  }
}

module.exports = { requestMobileCall };
