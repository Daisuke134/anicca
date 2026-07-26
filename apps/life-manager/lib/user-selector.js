// lib/user-selector.js — C4 (VCSDD life-manager-cost-connect-reliability). SSOT for which calendar
// providers get wake calls. Pipedream Connect provisions users as `pipedream_gcal`; the old code
// hardcoded `eq.composio_gcal` at two sites, so Pipedream users got zero wakes. Both scheduler sites
// now share this one filter.
"use strict";

const { compActive } = require("./comp-window.js");

const WAKE_CALENDAR_PROVIDERS = ["composio_gcal", "pipedream_gcal"];

// PostgREST filter fragment selecting any supported calendar provider.
function calendarProviderFilter() {
  return `calendar_provider=in.(${WAKE_CALENDAR_PROVIDERS.join(",")})`;
}

// Full scheduler cohort contract. Any readiness check selecting a DAILY target must reuse this
// fragment so phone/paid/provider eligibility cannot drift from scheduler.js.
//
// COMP WINDOW: a comped user is unpaid in the database (lib/billing.js is the only writer of `paid`),
// so leaving `paid=is.true` in the query would hand them a working onboarding and then zero wakes,
// travel or asks. While LM_COMP_UNTIL is in the future the predicate drops out; the moment it expires
// the fragment is byte-for-byte what it always was. Args exist for tests — production calls it bare.
function schedulerCohortFilter(env, nowMs) {
  const paidPredicate = compActive(env || process.env, nowMs) ? "" : "paid=is.true&";
  return `phone=not.is.null&${paidPredicate}${calendarProviderFilter()}`;
}

module.exports = { WAKE_CALENDAR_PROVIDERS, calendarProviderFilter, schedulerCohortFilter };
