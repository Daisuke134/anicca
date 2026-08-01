"use strict";

const { createAuthAwareLumaDailyDriver } = require("./luma-daily-driver-auth.js");
const { discoverLumaTokyo } = require("./luma-discovery.js");
const { inspectLumaEvent } = require("./luma-event-detail.js");
const { inspectLumaDateInventory } = require("./luma-date-inventory.js");
const { createLumaBrowserProvider } = require("./luma-browser-provider.js");
const { inferEventPreferenceRanking } = require("./event-preference-ranking.js");
const { inferEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");
const { planConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const {
  calendarEligibleLumaCandidates,
  evaluateCalendarCandidateGate,
} = require("./calendar-candidate-gate.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { syncVerifiedRegistrationToGoogleCalendar } = require("./connector-calendar-sync.js");
const { createConnpassApiClient } = require("./connpass-api-client.js");
const {
  createEventSourceCapabilities,
  executeEventSourceHandoff,
  planEventSourceHandoff,
} = require("./event-source-handoff.js");

function invalid() {
  return new Error("Connector events pack configuration unavailable");
}

function createConnectorEventsPack(options = {}) {
  const dailyDriver = options.dailyDriver;
  const auth = options.auth;
  const evidenceStore = options.evidenceStore;
  if (
    !dailyDriver
    || typeof dailyDriver.withLumaPage !== "function"
    || !auth
    || typeof auth.ensureAuthenticated !== "function"
    || !evidenceStore
    || typeof evidenceStore.record !== "function"
  ) throw invalid();

  const createAuthAwareDriver = options.createAuthAwareDriver || createAuthAwareLumaDailyDriver;
  const createProvider = options.createProvider || createLumaBrowserProvider;
  const discover = options.discover || discoverLumaTokyo;
  const inspect = options.inspect || inspectLumaEvent;
  const inspectDateInventory = options.inspectDateInventory || inspectLumaDateInventory;
  const rankPreferences = options.rankPreferences || inferEventPreferenceRanking;
  const evaluateGoalSerendipity = options.evaluateGoalSerendipity || inferEventGoalSerendipity;
  const createSourceCapabilities = options.createSourceCapabilities || createEventSourceCapabilities;
  const planSourceHandoff = options.planSourceHandoff || planEventSourceHandoff;
  const executeSourceHandoff = options.executeSourceHandoff || executeEventSourceHandoff;
  const createConnpassClient = options.createConnpassClient || createConnpassApiClient;
  const runCandidateSequence = options.runCandidateSequence || runLumaCandidateSequence;
  const planCoverageContinuation = options.planCoverageContinuation || planConnectorCoverageContinuation;
  const selectCalendarEligibleCandidates = options.selectCalendarEligibleCandidates || calendarEligibleLumaCandidates;
  const inspectBusyCalendar = options.inspectBusyCalendar || inspectGoogleCalendarBusyInventory;
  const evaluateCalendarGate = options.evaluateCalendarGate || evaluateCalendarCandidateGate;
  const syncRegistrationCalendar = options.syncRegistrationCalendar || syncVerifiedRegistrationToGoogleCalendar;
  const authAwareDriver = createAuthAwareDriver({ dailyDriver, auth });
  if (!authAwareDriver || typeof authAwareDriver.withLumaPage !== "function") throw invalid();
  const provider = createProvider({
    dailyDriver: authAwareDriver,
    evidenceStore,
    now: options.now,
  });
  if (
    !provider
    || typeof provider.inspectRegistration !== "function"
    || typeof provider.submitRegistration !== "function"
  ) throw invalid();

  return Object.freeze({
    provider,
    discoverTokyo(extra = {}) {
      return discover({ ...extra, dailyDriver: authAwareDriver });
    },
    inspectEvent(canonicalUrl, extra = {}) {
      return inspect({ ...extra, dailyDriver: authAwareDriver, canonicalUrl });
    },
    readDateInventory(coverage, extra = {}) {
      return inspectDateInventory({
        coverage,
        now: extra.now,
        discoverTokyo: () => discover({
          dailyDriver: authAwareDriver,
          maxRounds: extra.maxRounds,
          stableEndRounds: extra.stableEndRounds,
        }),
        inspectEvent: (canonicalUrl) => inspect({
          dailyDriver: authAwareDriver,
          canonicalUrl,
        }),
      });
    },
    rankDatePreferences(dateInventory, date, preferences, extra = {}) {
      return rankPreferences({ dateInventory, date, preferences }, extra);
    },
    evaluateDateGoals(dateInventory, preferenceRanking, goals, extra = {}) {
      return evaluateGoalSerendipity({ dateInventory, preferenceRanking, goals }, extra);
    },
    runSameDayCandidates(candidates, attempt) {
      return runCandidateSequence({ candidates, attempt });
    },
    runCalendarGatedSameDay(dateInventory, calendarGate, attempt) {
      const candidates = selectCalendarEligibleCandidates(dateInventory, calendarGate);
      return runCandidateSequence({ candidates, attempt });
    },
    readBusyCalendar(calendar, window = {}) {
      return inspectBusyCalendar({ calendar, ...window });
    },
    gateDateCalendar(dateInventory, busyInventory, date, homeLocation, routeMinutes) {
      return evaluateCalendarGate({
        dateInventory, busyInventory, date, homeLocation, routeMinutes,
      });
    },
    syncRegistrationCalendar(input) {
      return syncRegistrationCalendar(input);
    },
    planCoverageContinuation(coverage, observedOutcomes, now) {
      return planCoverageContinuation({ coverage, observedOutcomes, now });
    },
    handoffEventSource(date, lumaOutcome, extra = {}) {
      const connpassApiKey = String(extra.connpassApiKey == null ? "" : extra.connpassApiKey);
      const capabilities = createSourceCapabilities({ connpassApiKey });
      const plan = planSourceHandoff({ date, lumaOutcome, capabilities });
      const connpassClient = capabilities.sources
        ? (capabilities.sources.connpass.discovery_allowed
          ? createConnpassClient({ apiKey: connpassApiKey })
          : undefined)
        : (connpassApiKey ? createConnpassClient({ apiKey: connpassApiKey }) : undefined);
      return executeSourceHandoff({ plan, connpassClient });
    },
  });
}

module.exports = { createConnectorEventsPack };
