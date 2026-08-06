"use strict";

const { DAILY_DRIVER_CDP, createCloakBrowserDailyDriver } = require("./cloakbrowser-daily-driver.js");
const { createLumaDailyDriverAuth } = require("./luma-daily-driver-auth.js");
const { createGogLumaCodeReader } = require("./gog-luma-code-reader.js");
const { createGogLumaConfirmationReader } = require("./gog-luma-confirmation-reader.js");
const { createConnectorEventsPack } = require("./connector-events-pack.js");
const { createLumaEvidenceStore } = require("./luma-evidence-store.js");
const { createLumaConfirmationMailStore } = require("./luma-confirmation-mail.js");
const { createLumaTicketQrStore } = require("./luma-ticket-qr.js");
const { makeGogCalendar } = require("./transport/calendar-gog.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedLumaEventDetail } = require("./luma-event-detail.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedLumaCandidateSequence } = require("./luma-candidate-loop.js");
const {
  buildRollingEventCoverage,
  isVerifiedRollingEventCoverage,
} = require("./rolling-event-coverage.js");
const { isVerifiedConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const { readConnectorProfile, isVerifiedConnectorProfile } = require("./connector-profile.js");
const { runConnectorLunaJudgment } = require("./connector-luna-judgment.js");
const {
  createEventSpendPolicy,
  isVerifiedEventSpendSequence,
} = require("./event-spend-policy.js");
const { isVerifiedEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { runNativeConnectorWrite } = require("./connector-native-write-pipeline.js");
const { classifyConnectorCandidateOutcome } = require("./connector-candidate-outcome.js");
const {
  activeSuppressedEventRefs,
  latestCandidateAttempts,
} = require("./connector-candidate-suppression.js");
const { createConnectorRouteMinutes } = require("./connector-route-minutes.js");
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

function passCandidateBudget(value) {
  if (value == null) return Number.MAX_SAFE_INTEGER;
  const budget = Number(value);
  if (!Number.isSafeInteger(budget) || budget < 1 || budget > 100) unavailable();
  return budget;
}

function resumeCursor(value) {
  if (value == null) return null;
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "date,event_ref,observed_at,status"
    || value.status !== "resume_after"
    || !/^\d{4}-\d{2}-\d{2}$/.test(String(value.date || ""))
    || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(value.event_ref || ""))
  ) unavailable();
  exactInstant(value.observed_at);
  return Object.freeze({ ...value });
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

function defaultCreateAuth(options = {}) {
  const email = requiredText(options.email);
  return createLumaDailyDriverAuth({
    dailyDriver: options.dailyDriver,
    email,
    name: requiredText(options.name),
    readLoginCode: createGogLumaCodeReader({
      gogPath: options.gogBin,
      env: {
        ...process.env,
        GOG_ACCOUNT: email,
        GOG_KEYRING_PASSWORD: requiredText(options.gogKeyring),
      },
    }),
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

function localDate(instant, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
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
  let failureCode = "CONNECTOR_NATIVE_CONFIG_FAILED";
  try {
    const config = input && input.config;
    const deps = input && input.deps && typeof input.deps === "object" ? input.deps : {};
    if (!config || typeof config !== "object" || Array.isArray(config)) unavailable();

    const tenantId = requiredText(config.tenantId);
    const timeZone = requiredText(config.timeZone);
    const now = exactInstant(config.now);
    const evidenceDir = absoluteDirectory(config.evidenceDir);
    const calendarAccount = requiredText(config.calendarAccount);
    let coverage = buildRollingEventCoverage({
      tenantId,
      timeZone,
      now,
      resolvedDays: [],
    });
    if (!isVerifiedRollingEventCoverage(coverage)) unavailable();

    const createDailyDriver = factory(deps, "createDailyDriver", defaultCreateDailyDriver);
    const createAuth = factory(deps, "createAuth", defaultCreateAuth);
    const createEvidenceStore = factory(deps, "createEvidenceStore", createLumaEvidenceStore);
    const createCalendar = factory(deps, "createCalendar", makeGogCalendar);
    const createPack = factory(deps, "createPack", createConnectorEventsPack);

    const dailyDriver = createDailyDriver({
      endpoint: DAILY_DRIVER_CDP,
      connectOverCDP: deps.connectOverCDP,
    });
    if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") unavailable();
    const auth = createAuth({
      dailyDriver,
      email: config.lumaEmail,
      name: config.lumaName,
      gogBin: config.gogBin,
      gogKeyring: config.gogKeyring,
    });
    if (!auth || typeof auth.ensureAuthenticated !== "function") unavailable();
    const evidenceStore = createEvidenceStore({ dataDir: evidenceDir });
    if (
      !evidenceStore
      || typeof evidenceStore.record !== "function"
      || typeof evidenceStore.readExternalReceipt !== "function"
      || typeof evidenceStore.readArtifact !== "function"
    ) unavailable();
    const calendar = createCalendar({
      account: calendarAccount,
      bin: config.gogBin,
      keyring: config.gogKeyring,
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

    failureCode = "CONNECTOR_NATIVE_AUTH_FAILED";
    const authentication = await auth.ensureAuthenticated();
    if (!authentication || authentication.status !== "authenticated") unavailable();
    const deliveredReceipts = Array.isArray(config.deliveredReceipts) ? config.deliveredReceipts : [];
    if (deliveredReceipts.length > 0) {
      if (typeof pack.inspectEvent !== "function") unavailable();
      const restored = new Map();
      for (const receipt of deliveredReceipts) {
        if (
          !receipt || typeof receipt !== "object" || Array.isArray(receipt)
          || !/^luma-event:\/\/event\/[A-Za-z0-9_-]+$/.test(String(receipt.event_ref || ""))
          || !/^calendar-evidence:\/\/google\/event\/[0-9a-f]{64}$/.test(String(receipt.calendar_event_ref || ""))
        ) unavailable();
        const slug = receipt.event_ref.slice("luma-event://event/".length);
        const detail = await pack.inspectEvent(`https://luma.com/${slug}`, { now });
        if (!isVerifiedLumaEventDetail(detail) || detail.event_ref !== receipt.event_ref) unavailable();
        const date = localDate(detail.starts_at, timeZone);
        if (!coverage.days.some((day) => day.date === date)) continue;
        const refs = restored.get(date) || [];
        refs.push(receipt.calendar_event_ref);
        restored.set(date, refs);
      }
      coverage = buildRollingEventCoverage({
        tenantId, timeZone, now,
        resolvedDays: [...restored].map(([date, evidenceRefs]) => ({
          date, status: "covered_new", evidence_refs: [...new Set(evidenceRefs)],
        })),
      });
      if (!isVerifiedRollingEventCoverage(coverage)) unavailable();
    }
    failureCode = "CONNECTOR_NATIVE_INVENTORY_FAILED";
    const dateInventory = await pack.readDateInventory(coverage, { now });
    if (
      !isVerifiedLumaDateInventory(dateInventory)
      || dateInventory.coverage_snapshot_id !== coverage.coverage_snapshot_id
    ) unavailable();
    const timeMin = midnight(coverage.window_start_date, timeZone);
    const timeMax = midnight(nextDate(coverage.window_end_date), timeZone);
    failureCode = "CONNECTOR_NATIVE_CALENDAR_READ_FAILED";
    const busyInventory = await pack.readBusyCalendar(calendar, { timeMin, timeMax, timeZone, now });
    if (!isVerifiedGoogleCalendarBusyInventory(busyInventory) || busyInventory.transport !== "gog") unavailable();

    let write = null;
    const candidateAttempts = [];
    const candidateBudget = passCandidateBudget(config.passCandidateBudget);
    const inputCursor = resumeCursor(config.cursor);
    let outputCursor = null;
    let attemptCount = 0;
    const suppressedEventRefs = activeSuppressedEventRefs({
      attempts: Array.isArray(config.candidateAttempts) ? config.candidateAttempts : [],
      now,
    });
    const latestAttempts = latestCandidateAttempts({
      attempts: Array.isArray(config.candidateAttempts) ? config.candidateAttempts : [],
      now,
    }).latest;
    if (Object.hasOwn(config, "profilePath")) {
      const readProfile = factory(deps, "readProfile", readConnectorProfile);
      const verifyProfile = factory(deps, "isVerifiedConnectorProfile", isVerifiedConnectorProfile);
      const runLunaJudgment = factory(deps, "runLunaJudgment", runConnectorLunaJudgment);
      const verifyGoalDecision = factory(
        deps, "isVerifiedEventGoalSerendipity", isVerifiedEventGoalSerendipity,
      );
      const gateDateCalendar = factory(deps, "gateDateCalendar", (...args) => pack.gateDateCalendar(...args));
      const createRouteMinutes = factory(deps, "createRouteMinutes", createConnectorRouteMinutes);
      const createSpendPolicy = factory(deps, "createSpendPolicy", createEventSpendPolicy);
      const planDateSpend = factory(deps, "planDateSpend", (...args) => pack.planDateSpend(...args));
      const verifySpendSequence = factory(
        deps, "isVerifiedEventSpendSequence", isVerifiedEventSpendSequence,
      );
      const runNativeWrite = factory(deps, "runNativeWrite", runNativeConnectorWrite);
      const createConfirmationReader = factory(
        deps, "createConfirmationReader", createGogLumaConfirmationReader,
      );
      const createConfirmationStore = factory(
        deps, "createConfirmationStore", createLumaConfirmationMailStore,
      );
      const createTicketStore = factory(deps, "createTicketStore", createLumaTicketQrStore);
      failureCode = "CONNECTOR_NATIVE_PROFILE_FAILED";
      const profile = readProfile({ tenantId, path: config.profilePath });
      if (!verifyProfile(profile) || profile.tenant_id !== tenantId || profile.timezone !== timeZone) unavailable();
      const judgmentDays = dateInventory.days.filter((day) => (
        coverage.days.some((coverageDay) => coverageDay.date === day.date && coverageDay.status === "open")
        && Array.isArray(day.events) && day.events.length > 0
      ));
      if (judgmentDays.length === 0) unavailable();
      const routeMinutes = createRouteMinutes({
        mapsKey: requiredText(config.mapsKey),
        homeLocation: requiredText(config.homeLocation),
      });
      const lumaEmail = requiredText(config.lumaEmail);
      const confirmationReader = createConfirmationReader({
        gogPath: config.gogBin,
        env: {
          ...process.env,
          GOG_ACCOUNT: lumaEmail,
          GOG_KEYRING_PASSWORD: requiredText(config.gogKeyring),
        },
      });
      const confirmationStore = createConfirmationStore({ dataDir: evidenceDir });
      const ticketStore = createTicketStore({ dataDir: evidenceDir });
      if (
        typeof confirmationReader !== "function"
        || !confirmationStore || typeof confirmationStore.record !== "function"
        || !ticketStore || typeof ticketStore.record !== "function"
        || typeof ticketStore.readArtifact !== "function"
        || typeof pack.captureLumaTicketQr !== "function"
      ) unavailable();
      const policy = await createSpendPolicy({ tenantId, limits: profile.spend_policy && profile.spend_policy.limits });
      let selected = false;
      judgmentLoop: for (const judgmentDay of judgmentDays) {
        if (inputCursor && judgmentDay.date < inputCursor.date) continue;
        failureCode = "CONNECTOR_NATIVE_CALENDAR_GATE_FAILED";
        const calendarGate = await gateDateCalendar(
          dateInventory, busyInventory, judgmentDay.date, requiredText(config.homeLocation), routeMinutes,
        );
        if (!calendarGate || !Array.isArray(calendarGate.candidates)) unavailable();
        if (!calendarGate.candidates.some((candidate) => candidate && candidate.eligible === true)) continue;
        failureCode = "CONNECTOR_NATIVE_LUNA_FAILED";
        const goalDecision = await runLunaJudgment({
          dateInventory,
          profile,
          date: judgmentDay.date,
          evidenceDir: absoluteDirectory(config.lunaEvidenceDir),
          repoRoot: config.repoRoot,
          runnerPath: config.runnerPath,
        });
        if (!verifyGoalDecision(goalDecision) || goalDecision.ranked_events.length === 0) unavailable();
        failureCode = "CONNECTOR_NATIVE_SPEND_GATE_FAILED";
        const spendSequence = await planDateSpend(policy, dateInventory, calendarGate, goalDecision);
        if (!verifySpendSequence(spendSequence)) unavailable();
        let resumableCandidates = spendSequence.ordered_candidates;
        if (inputCursor && judgmentDay.date === inputCursor.date) {
          const cursorIndex = resumableCandidates.findIndex(
            (candidate) => candidate.event_ref === inputCursor.event_ref,
          );
          if (cursorIndex >= 0) resumableCandidates = resumableCandidates.slice(cursorIndex + 1);
        }
        const orderedCandidates = resumableCandidates.filter(
          (candidate) => !suppressedEventRefs.has(candidate.event_ref),
        );
        if (orderedCandidates.length === 0) continue;
        selected = true;
        failureCode = "CONNECTOR_NATIVE_WRITE_FAILED";
        for (const chosen of orderedCandidates) {
          const selectedRef = chosen.event_ref;
          const selectedEvent = judgmentDay.events.find((event) => event && event.event_ref === selectedRef);
          if (!selectedEvent || chosen.canonical_url !== selectedEvent.canonical_url) unavailable();
          const previousAttempt = latestAttempts.get(selectedRef);
          if (previousAttempt && previousAttempt.outcome === "unknown_effect") {
            const proof = await pack.provider.inspectRegistration({
              tenant_id: tenantId,
              event_ref: selectedRef,
              canonical_url: selectedEvent.canonical_url,
            });
            if (!proof || !["absent", "registered", "login_required", "unavailable", "unknown"].includes(proof.state)) {
              unavailable();
            }
            if (proof.state !== "registered") {
              const reconciledAbsent = ["absent", "unavailable"].includes(proof.state);
              candidateAttempts.push(Object.freeze({
                event_ref: selectedRef,
                outcome: reconciledAbsent ? "known_no_effect" : "unknown_effect",
                safe_reason: reconciledAbsent ? "LUMA_RECONCILED_ABSENT" : "CONNECTOR_EFFECT_UNKNOWN",
                observed_at: now,
                retry_after: reconciledAbsent ? now : null,
              }));
              break judgmentLoop;
            }
          }
          write = await runNativeWrite({
            application: {
              tenantId,
              eventRef: selectedRef,
              eventUrl: selectedEvent.canonical_url,
              eventStartIso: selectedEvent.starts_at,
              identityRef: profile.identity_ref,
              browserProfileRef: profile.browser_profile_ref,
              calendarRef: profile.calendar_ref,
            },
            profile,
            dateInventory,
            currentCoverage: coverage,
            busyInventory,
            goalDecision,
            calendar,
            calendarId: requiredText(config.calendarId),
            telegramTarget: requiredText(config.telegramTarget),
            calendarCoverageUrl: requiredText(config.calendarCoverageUrl),
            registrationIdentity: requiredText(config.lumaName),
            now,
          }, {
            provider: pack.provider,
            readExternalReceipt: evidenceStore.readExternalReceipt,
            readArtifact: evidenceStore.readArtifact,
            readLumaConfirmation: ({ registrationStartedAt }) => confirmationReader({
              account: lumaEmail,
              afterMs: Date.parse(registrationStartedAt),
            }),
            recordLumaConfirmation: confirmationStore.record,
            captureLumaTicketQr: (binding) => pack.captureLumaTicketQr(binding),
            recordLumaTicketQr: ticketStore.record,
            readTicketArtifact: ticketStore.readArtifact,
            fetchImpl: globalThis.fetch,
            ...(deps.writeDependencies || {}),
          });
          const candidateOutcome = classifyConnectorCandidateOutcome(write);
          candidateAttempts.push(Object.freeze({
            event_ref: candidateOutcome.event_ref,
            outcome: candidateOutcome.classification,
            safe_reason: candidateOutcome.error_code || write.outcome,
            observed_at: now,
            retry_after: null,
          }));
          attemptCount += 1;
          if (
            candidateOutcome.classification === "known_no_effect"
            && attemptCount >= candidateBudget
          ) {
            outputCursor = Object.freeze({
              status: "resume_after",
              date: judgmentDay.date,
              event_ref: selectedRef,
              observed_at: now,
            });
            break judgmentLoop;
          }
          if (candidateOutcome.classification !== "known_no_effect") break judgmentLoop;
        }
      }
      if (!selected) unavailable();
    }

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
      write,
      candidate_attempts: Object.freeze([...candidateAttempts]),
      cursor: outputCursor,
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
    const error = new Error("Connector native runtime unavailable");
    error.code = failureCode;
    throw error;
  }
}

module.exports = { runNativeConnectorPass };
