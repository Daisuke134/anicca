"use strict";

const { MobileError, maskPhone, normalizeLocale, safeTimeZone } = require("./mobile-utils.js");

function calendarState(row) {
  if (row && typeof row.calendar_status === "string") {
    return ["connected", "action_required", "error", "disconnected"].includes(row.calendar_status)
      ? row.calendar_status
      : "error";
  }
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
  if (row.uid && String(row.uid) !== String(scope.uid)) throw new MobileError("scope_mismatch", "The authenticated scope does not match the requested account.", 403);
  const locale = normalizeLocale(row.product_locale || row.productLocale || scope.productLocale || "en");
  const timezone = safeTimeZone(row.time_zone || row.timezone || scope.timezone || "UTC");
  const phone = row.phone || null;
  const analysis = typeof store.readAnalysisState === "function" ? await store.readAnalysisState(scope) : { status: "idle" };
  const internalPhases = new Set(["reading_events", "checking_locations", "calculating_route"]);
  const allowedStatuses = new Set(["idle", "running", "route_ready", "needs_information", "no_upcoming_event", "route_unavailable", "failed"]);
  const rawStatus = analysis && typeof analysis.status === "string" ? analysis.status : "idle";
  const status = internalPhases.has(rawStatus) ? "running" : (allowedStatuses.has(rawStatus) ? rawStatus : "failed");
  const callsEnabled = (row.calls_enabled === true || row.callsEnabled === true) && Boolean(phone);
  const callLanguage = callsEnabled ? (row.call_language || row.callLanguage || null) : null;
  const calendarStatus = calendarState(row);
  const billingStatus = row.billing_status || row.billingStatus || (row.paid === true ? "active" : "payment_required");
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
    calendar: { status: calendarStatus },
    offer: { status: "available" },
    analysis: { status },
    connections: {
      calendar: { status: calendarStatus, provider: "google_calendar" },
      phone: { status: phone ? "connected" : "missing", masked: maskPhone(phone) },
      billing: { status: ["active", "payment_required", "past_due"].includes(billingStatus) ? billingStatus : "payment_required" },
    },
    subscriptionOffer: { status: "available" },
  };
}

module.exports = { readMobileBootstrap, calendarState };
