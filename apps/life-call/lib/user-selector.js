// lib/user-selector.js — C4 (VCSDD life-manager-cost-connect-reliability). SSOT for which calendar
// providers get wake calls. Pipedream Connect provisions users as `pipedream_gcal`; the old code
// hardcoded `eq.composio_gcal` at two sites, so Pipedream users got zero wakes. Both scheduler sites
// now share this one filter.
"use strict";

const WAKE_CALENDAR_PROVIDERS = ["composio_gcal", "pipedream_gcal"];

// PostgREST filter fragment selecting any supported calendar provider.
function calendarProviderFilter() {
  return `calendar_provider=in.(${WAKE_CALENDAR_PROVIDERS.join(",")})`;
}

// Full scheduler cohort contract. Any readiness check selecting a DAILY target must reuse this
// fragment so phone/paid/provider eligibility cannot drift from scheduler.js.
function schedulerCohortFilter() {
  return `phone=not.is.null&paid=is.true&${calendarProviderFilter()}`;
}

module.exports = { WAKE_CALENDAR_PROVIDERS, calendarProviderFilter, schedulerCohortFilter };
