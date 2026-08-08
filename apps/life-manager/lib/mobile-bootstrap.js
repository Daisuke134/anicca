"use strict";

const { MobileError, maskPhone, normalizeLocale, safeTimeZone } = require("./mobile-utils.js");

function calendarState(row) {
  if (row && typeof row.calendar_status === "string") return row.calendar_status;
  const provider = row && (row.calendar_provider || row.calendarProvider);
  const account = row && (row.gmail_account_id || row.gmailAccountId);
  if (provider && account) return "connected";
  if (provider || account) return "action_required";
  if (row && row.calendar_error) return "error";
  return "disconnected";
}

async function readMobileBootstrap(scope, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const store = deps.store;
  if (!store || typeof store.readUser !== "function") throw new MobileError("bootstrap_unavailable", "Bootstrap storage is unavailable.", 503, true);
  const row = await store.readUser(scope);
  if (!row) throw new MobileError("account_not_found", "The Life Manager account was not found.", 404);
  const locale = normalizeLocale(row.product_locale || row.productLocale || scope.productLocale || "en");
  const timezone = safeTimeZone(row.time_zone || row.timezone || scope.timezone || "UTC");
  const phone = row.phone || null;
  const analysis = typeof store.readAnalysisState === "function" ? await store.readAnalysisState(scope) : { status: "idle" };
  const status = analysis && typeof analysis.status === "string" ? analysis.status : "idle";
  const callsEnabled = row.calls_enabled === true || row.callsEnabled === true;
  const callLanguage = row.call_language || row.callLanguage || null;
  return {
    user: {
      id: String(row.uid || scope.uid),
      name: row.name || null,
      productLocale: locale,
      timezone,
      home: { status: row.home_address || row.home ? "ready" : "missing", display: row.home_address || row.home || null },
      phone: { status: phone ? "configured" : "missing", masked: maskPhone(phone) },
      callsEnabled,
      callLanguage: callLanguage ? normalizeLocale(callLanguage) : null,
    },
    calendar: { status: calendarState(row) },
    offer: { status: "available" },
    analysis: { status },
  };
}

module.exports = { readMobileBootstrap, calendarState };
