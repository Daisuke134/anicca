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
const { captureOfficialLumaTicketQr } = require("./luma-ticket-qr.js");
const {
  buildConnectorCoverageTelegramMessage,
  deliverConnectorCoverageTelegram,
} = require("./connector-coverage-telegram.js");
const {
  buildVerifiedRegistrationCoverageEvidence,
  proveAllDayCalendarUnavailable,
  proveCalendarGateUnavailable,
  rebuildRollingEventCoverage,
} = require("./connector-coverage-assembler.js");
const {
  buildEventSpendSequence,
  eventSpendDecisionForSequence,
  inspectSavedLumaPaymentMethod,
} = require("./event-spend-policy.js");
const { createConnpassApiClient } = require("./connpass-api-client.js");
const { discoverConnpassDateWithBrowser } = require("./connpass-browser-discovery.js");
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
  const discoverConnpassDate = options.discoverConnpassDate || discoverConnpassDateWithBrowser;
  const planCoverageContinuation = options.planCoverageContinuation || planConnectorCoverageContinuation;
  const selectCalendarEligibleCandidates = options.selectCalendarEligibleCandidates || calendarEligibleLumaCandidates;
  const inspectBusyCalendar = options.inspectBusyCalendar || inspectGoogleCalendarBusyInventory;
  const evaluateCalendarGate = options.evaluateCalendarGate || evaluateCalendarCandidateGate;
  const syncRegistrationCalendar = options.syncRegistrationCalendar || syncVerifiedRegistrationToGoogleCalendar;
  const captureTicketQr = options.captureTicketQr || captureOfficialLumaTicketQr;
  const planSpendSequence = options.planSpendSequence || buildEventSpendSequence;
  const spendDecisionForSequence = options.spendDecisionForSequence || eventSpendDecisionForSequence;
  const buildCoverageTelegram = options.buildCoverageTelegram || buildConnectorCoverageTelegramMessage;
  const deliverCoverageTelegram = options.deliverCoverageTelegram || deliverConnectorCoverageTelegram;
  const buildRegistrationCoverageEvidence = options.buildRegistrationCoverageEvidence
    || buildVerifiedRegistrationCoverageEvidence;
  const proveUnavailableDay = options.proveUnavailableDay || proveAllDayCalendarUnavailable;
  const rebuildCoverage = options.rebuildCoverage || rebuildRollingEventCoverage;
  const authAwareDriver = createAuthAwareDriver({ dailyDriver, auth });
  if (!authAwareDriver || typeof authAwareDriver.withLumaPage !== "function") throw invalid();
  const provider = createProvider({
    dailyDriver: authAwareDriver,
    evidenceStore,
    readLumaFormProfile: options.readLumaFormProfile,
    agenticRegister: options.agenticRegister,
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
        requiredCanonicalUrls: extra.requiredCanonicalUrls,
      });
    },
    rankDatePreferences(dateInventory, date, preferences, extra = {}) {
      return rankPreferences({ dateInventory, date, preferences }, extra);
    },
    evaluateDateGoals(dateInventory, preferenceRanking, goals, extra = {}) {
      return evaluateGoalSerendipity({ dateInventory, preferenceRanking, goals }, extra);
    },
    readSavedPaymentMethod() {
      if (typeof provider.inspectSavedPaymentMethod !== "function") throw invalid();
      return inspectSavedLumaPaymentMethod({ inspect: () => provider.inspectSavedPaymentMethod() });
    },
    runSameDayCandidates(candidates, attempt) {
      return runCandidateSequence({ candidates, attempt });
    },
    runCalendarGatedSameDay(dateInventory, calendarGate, attempt) {
      const candidates = selectCalendarEligibleCandidates(dateInventory, calendarGate);
      return runCandidateSequence({ candidates, attempt });
    },
    planDateSpend(policy, dateInventory, calendarGate, goalDecision) {
      return planSpendSequence({ policy, dateInventory, calendarGate, goalDecision });
    },
    runSpendGatedSameDay(spendSequence, attempt) {
      if (!spendSequence || !Array.isArray(spendSequence.ordered_candidates)) throw invalid();
      const candidates = spendSequence.ordered_candidates.map((candidate) => Object.freeze({
        event_ref: candidate.event_ref,
        canonical_url: candidate.canonical_url,
      }));
      return runCandidateSequence({
        candidates,
        attempt: (candidate) => attempt(
          candidate,
          spendDecisionForSequence(spendSequence, candidate.event_ref),
        ),
      });
    },
    readBusyCalendar(calendar, window = {}) {
      return inspectBusyCalendar({ calendar, ...window });
    },
    gateDateCalendar(dateInventory, busyInventory, date) {
      return evaluateCalendarGate({ dateInventory, busyInventory, date });
    },
    syncRegistrationCalendar(input) {
      return syncRegistrationCalendar(input);
    },
    captureLumaTicketQr(binding) {
      if (!binding || typeof binding !== "object" || !/^https:\/\/(?:www\.)?(?:luma\.com|lu\.ma)\//i.test(
        String(binding.event_url || ""),
      )) throw invalid();
      return authAwareDriver.withLumaPage(binding.event_url, (page) => (
        captureTicketQr(page, binding, { observedAt: options.now })
      ));
    },
    buildCoverageTelegram(input) {
      return buildCoverageTelegram(input);
    },
    deliverCoverageTelegram(input, dependencies = {}) {
      return deliverCoverageTelegram(input, dependencies);
    },
    buildRegistrationCoverageEvidence(input) {
      return buildRegistrationCoverageEvidence(input);
    },
    proveUnavailableDay(input) {
      return proveUnavailableDay(input);
    },
    proveCalendarGateUnavailable(input) {
      return proveCalendarGateUnavailable(input);
    },
    rebuildCoverage(input) {
      return rebuildCoverage(input);
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
    discoverConnpassDate(date, extra = {}) {
      return discoverConnpassDate({
        date,
        timeZone: extra.timeZone,
        dailyDriver,
      });
    },
  });
}

module.exports = { createConnectorEventsPack };
