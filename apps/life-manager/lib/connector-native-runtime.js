"use strict";

const { DAILY_DRIVER_CDP, createCloakBrowserDailyDriver } = require("./cloakbrowser-daily-driver.js");
const { createReadOnlyLumaSessionAuth } = require("./luma-daily-driver-auth.js");
const { createConnectorEventsPack } = require("./connector-events-pack.js");
const { createLumaEvidenceStore } = require("./luma-evidence-store.js");
const { makeGogCalendar } = require("./transport/calendar-gog.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedLumaCandidateSequence } = require("./luma-candidate-loop.js");
const {
  buildRollingEventCoverage,
  isVerifiedRollingEventCoverage,
} = require("./rolling-event-coverage.js");
const { isVerifiedConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

function unavailable() {
  throw new Error("Connector native runtime unavailable");
}

function exactInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) unavailable();
  return new Date(milliseconds).toISOString();
}

function absoluteDirectory(value) {
  const path = require("node:path");
  const directory = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) unavailable();
  return directory;
}

function requiredText(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 512) unavailable();
  return text;
}

function nextDate(dateKey) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(dateKey))) unavailable();
  const [year, month, day] = dateKey.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(next)) unavailable();
  return next;
}

function midnight(dateKey, timeZone) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  if (![year, month, day].every(Number.isInteger)) unavailable();
  return zonedSlotInstant({ year, month, day }, "00:00", timeZone);
}

function defaultCreateDailyDriver(options = {}) {
  const { chromium } = require("playwright-core");
  const connectOverCDP = typeof options.connectOverCDP === "function"
    ? options.connectOverCDP
    : (endpoint) => chromium.connectOverCDP(endpoint);
  return createCloakBrowserDailyDriver({
    endpoint: DAILY_DRIVER_CDP,
    connectOverCDP,
  });
}

function factory(deps, name, fallback) {
  return typeof deps[name] === "function" ? deps[name] : fallback;
}

function eventCount(dateInventory) {
  if (!Array.isArray(dateInventory.days)) unavailable();
  return dateInventory.days.reduce((count, day) => (
    count + (Array.isArray(day && day.events) ? day.events.length : 0)
  ), 0);
}

function eventDate(dateInventory, eventRef) {
  if (!eventRef || !Array.isArray(dateInventory.days)) return null;
  const day = dateInventory.days.find((candidate) => (
    Array.isArray(candidate.events)
    && candidate.events.some((event) => event && event.event_ref === eventRef)
  ));
  return day && /^\d{4}-\d{2}-\d{2}$/.test(String(day.date)) ? day.date : null;
}

function candidateSummary(sequence) {
  switch (sequence.status) {
    case "next_provider_required":
      return Object.freeze({ status: "next_provider_required", outcome: "search_exhausted" });
    case "recovery_required":
      return Object.freeze({ status: "recovery_required", outcome: "recovery_required" });
    case "reconciliation_required":
      return Object.freeze({ status: "reconciliation_required", outcome: "reconciliation_required" });
    case "booked":
      // A provider receipt is not a completed local effect until the separately bounded
      // receipt verification and calendar synchronization boundary has run.
      return Object.freeze({ status: "booked", outcome: "reconciliation_required" });
    default:
      unavailable();
  }
}

function candidateObservation(dateInventory, sequence, summary) {
  const eventRef = sequence && sequence.candidate && sequence.candidate.event_ref
    ? sequence.candidate.event_ref
    : sequence && Array.isArray(sequence.skipped) && sequence.skipped.length > 0
      ? sequence.skipped.at(-1).event_ref
      : null;
  const date = eventDate(dateInventory, eventRef);
  return date ? Object.freeze({ date, observed_status: summary.outcome }) : null;
}

async function runNativeConnectorPass(input = {}) {
  try {
    const config = input && input.config;
    const deps = input && input.deps && typeof input.deps === "object" ? input.deps : {};
    if (!config || typeof config !== "object" || Array.isArray(config)) unavailable();

    const tenantId = requiredText(config.tenantId);
    const timeZone = requiredText(config.timeZone);
    const now = exactInstant(config.now);
    const evidenceDir = absoluteDirectory(config.evidenceDir);
    const calendarAccount = requiredText(config.calendarAccount);
    const coverage = buildRollingEventCoverage({
      tenantId,
      timeZone,
      now,
      resolvedDays: [],
    });
    if (!isVerifiedRollingEventCoverage(coverage)) unavailable();

    const createDailyDriver = factory(deps, "createDailyDriver", defaultCreateDailyDriver);
    const createAuth = factory(deps, "createAuth", createReadOnlyLumaSessionAuth);
    const createEvidenceStore = factory(deps, "createEvidenceStore", createLumaEvidenceStore);
    const createCalendar = factory(deps, "createCalendar", makeGogCalendar);
    const createPack = factory(deps, "createPack", createConnectorEventsPack);

    const dailyDriver = createDailyDriver({
      endpoint: DAILY_DRIVER_CDP,
      connectOverCDP: deps.connectOverCDP,
    });
    if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") unavailable();
    const auth = createAuth({ dailyDriver });
    if (!auth || typeof auth.ensureAuthenticated !== "function") unavailable();
    const evidenceStore = createEvidenceStore({ dataDir: evidenceDir });
    if (!evidenceStore || typeof evidenceStore.record !== "function") unavailable();
    const calendar = createCalendar({
      account: calendarAccount,
      bin: config.gogBin,
    });
    if (!calendar || calendar.kind !== "gog" || typeof calendar.ready !== "function" || !calendar.ready()) {
      unavailable();
    }
    const pack = createPack({ dailyDriver, auth, evidenceStore, now: () => now });
    if (
      !pack
      || typeof pack.readDateInventory !== "function"
      || typeof pack.readBusyCalendar !== "function"
      || typeof pack.planCoverageContinuation !== "function"
      || typeof pack.runSameDayCandidates !== "function"
    ) unavailable();

    const authentication = await auth.ensureAuthenticated();
    if (!authentication || authentication.status !== "authenticated") unavailable();
    const dateInventory = await pack.readDateInventory(coverage, { now });
    if (
      !isVerifiedLumaDateInventory(dateInventory)
      || dateInventory.coverage_snapshot_id !== coverage.coverage_snapshot_id
    ) unavailable();
    const timeMin = midnight(coverage.window_start_date, timeZone);
    const timeMax = midnight(nextDate(coverage.window_end_date), timeZone);
    const busyInventory = await pack.readBusyCalendar(calendar, { timeMin, timeMax, timeZone, now });
    if (!isVerifiedGoogleCalendarBusyInventory(busyInventory) || busyInventory.transport !== "gog") unavailable();

    let candidate = null;
    const observedOutcomes = [];
    const candidateConfigured = Object.hasOwn(config, "candidates") || Object.hasOwn(config, "attemptCandidate");
    if (candidateConfigured) {
      if (!Array.isArray(config.candidates) || typeof config.attemptCandidate !== "function") unavailable();
      const sequence = await pack.runSameDayCandidates(config.candidates, config.attemptCandidate);
      if (!isVerifiedLumaCandidateSequence(sequence)) unavailable();
      candidate = candidateSummary(sequence);
      const observation = candidateObservation(dateInventory, sequence, candidate);
      if (observation) observedOutcomes.push(observation);
    }

    const continuation = pack.planCoverageContinuation(coverage, observedOutcomes, now);
    if (!isVerifiedConnectorCoverageContinuation(continuation)) unavailable();
    const complete = coverage.counts.open === 0 && continuation.status === "complete";
    return Object.freeze({
      status: complete ? "complete" : "incomplete",
      coverage: Object.freeze({
        counts: coverage.counts,
        window_start_date: coverage.window_start_date,
        window_end_date: coverage.window_end_date,
      }),
      inventory: Object.freeze({
        complete: true,
        event_count: eventCount(dateInventory),
      }),
      calendar: Object.freeze({
        transport: "gog",
        all_calendars_read: true,
        calendar_count: busyInventory.calendar_count,
        busy_event_count: busyInventory.busy_event_count,
      }),
      candidate,
      continuation: Object.freeze({
        status: continuation.status,
        open_date_count: continuation.open_date_count,
        next_action: continuation.next_action,
      }),
      deferred_effects: Object.freeze({
        registration: "not_executed",
        receipt_verification: "not_executed",
        calendar_sync: "not_executed",
        telegram_delivery: "not_executed",
      }),
    });
  } catch {
    unavailable();
  }
}

module.exports = { runNativeConnectorPass };
