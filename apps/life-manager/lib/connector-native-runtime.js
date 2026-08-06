"use strict";

const path = require("node:path");
const { DAILY_DRIVER_CDP, createCloakBrowserDailyDriver } = require("./cloakbrowser-daily-driver.js");
const { createConnectorTabOwner } = require("./connector-tab-owner.js");
const { createConnectorTargetLease } = require("./connector-target-lease.js");
const { createConnectorBrowserTargetController } = require("./connector-browser-target-controller.js");
const { createLumaDailyDriverAuth } = require("./luma-daily-driver-auth.js");
const { createGogLumaCodeReader } = require("./gog-luma-code-reader.js");
const { createGogLumaConfirmationReader } = require("./gog-luma-confirmation-reader.js");
const { createConnectorEventsPack } = require("./connector-events-pack.js");
const { createLumaEvidenceStore } = require("./luma-evidence-store.js");
const { readLumaFormProfile } = require("./luma-form-profile.js");
const { readConnectorUserProfile } = require("./connector-user-profile.js");
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
const { buildConnectorDeterministicJudgment } = require("./connector-deterministic-judgment.js");
const { runConnectorAgenticRegistration } = require("./connector-agentic-registration.js");
const {
  createEventSpendPolicy,
  isVerifiedEventSpendSequence,
} = require("./event-spend-policy.js");
const { isVerifiedEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { runNativeConnectorWrite } = require("./connector-native-write-pipeline.js");
const { classifyConnectorCandidateOutcome } = require("./connector-candidate-outcome.js");
const { latestCandidateAttempts } = require("./connector-candidate-suppression.js");
const { createConnectorRouteMinutes } = require("./connector-route-minutes.js");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const { isVerifiedEventProviderRegistry } = require("./event-provider-registry.js");
const { advanceEventProviderCursor, createEventProviderCursor } = require("./event-provider-cursor.js");
const {
  buildConnpassBrowserHandoff,
  isVerifiedEventSourceHandoff,
} = require("./event-source-handoff.js");
const {
  calendarEligibleConnpassCandidates,
  evaluateConnpassCalendarCandidateGate,
  isVerifiedCalendarCandidateGate,
} = require("./calendar-candidate-gate.js");
const { buildEventProviderDateInventory } = require("./event-provider-date-inventory.js");
const { createConnpassBrowserProvider } = require("./connpass-browser-provider.js");
const { createConnpassEvidenceStore } = require("./connpass-evidence-store.js");
const {
  buildConnpassEventApplicationJob, executeConnpassRsvpJob,
} = require("./connpass-rsvp-adapter.js");

function unavailable() {
  throw new Error("Connector native runtime unavailable");
}

function calendarGateFailureCode(error, options = {}) {
  if (options.phase === "result") return "CONNECTOR_NATIVE_CALENDAR_GATE_RESULT_FAILED";
  return error && error.message === "Calendar candidate gate invalid"
    ? "CONNECTOR_NATIVE_CALENDAR_GATE_INPUT_FAILED"
    : "CONNECTOR_NATIVE_CALENDAR_GATE_EXECUTION_FAILED";
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

function absoluteFilePath(value) {
  const path = require("node:path");
  const file = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(file) || file === path.parse(file).root) unavailable();
  return file;
}

function requiredText(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > 512) unavailable();
  return text;
}

function capabilityVersion(value) {
  if (value == null) return null;
  const version = String(value).trim();
  if (!/^[a-z0-9][a-z0-9._-]{0,63}$/.test(version)) unavailable();
  return version;
}

function nextCursorInstant(cursor, now) {
  const previous = Date.parse(cursor.observed_at);
  const current = Date.parse(now);
  if (!Number.isFinite(previous) || !Number.isFinite(current)) unavailable();
  return new Date(Math.max(previous + 1, current)).toISOString();
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
    createTargetOwnership(browser) {
      const controller = createConnectorBrowserTargetController({
        browser,
        endpoint: DAILY_DRIVER_CDP,
      });
      const targetLease = createConnectorTargetLease({
        ledgerPath: absoluteFilePath(options.targetLeaseLedgerPath),
        probeTarget: (pageWebsocket) => controller.probe(pageWebsocket),
        closeTarget: (targetId) => controller.close(targetId),
      });
      return Object.freeze({
        controller,
        owner: createConnectorTabOwner({
          endpoint: DAILY_DRIVER_CDP,
          targetLease,
        }),
      });
    },
    tabOwnerReceiptPath: options.tabOwnerReceiptPath,
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
    const readPrivateLumaFormProfile = factory(deps, "readLumaFormProfile", readLumaFormProfile);
    const readPrivateUserProfile = factory(deps, "readConnectorUserProfile", readConnectorUserProfile);

    const dailyDriver = createDailyDriver({
      endpoint: DAILY_DRIVER_CDP,
      connectOverCDP: deps.connectOverCDP,
      tabOwnerReceiptPath: path.join(evidenceDir, "tab-owner.json"),
      targetLeaseLedgerPath: path.join(evidenceDir, "target-leases.json"),
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
    const lumaFormProfilePath = config.lumaFormProfilePath == null
      ? null : absoluteFilePath(config.lumaFormProfilePath);
    const userProfilePath = config.userProfilePath == null
      ? lumaFormProfilePath : absoluteFilePath(config.userProfilePath);
    const pack = createPack({
      dailyDriver,
      auth,
      evidenceStore,
      readLumaFormProfile: lumaFormProfilePath === null ? undefined : (() => (
        readPrivateLumaFormProfile({ path: lumaFormProfilePath })
      )),
      agenticRegister: (input) => runConnectorAgenticRegistration({
        ...input,
        profile: userProfilePath === null ? {} : readPrivateUserProfile({ path: userProfilePath }),
        evidenceDir,
        repoRoot: config.repoRoot,
        runnerPath: config.runnerPath,
      }),
      now: () => now,
    });
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

    const selection = {
      inventory_event_count: eventCount(dateInventory),
      calendar_gate_event_count: 0,
      calendar_eligible_count: 0,
      luna_ranked_count: 0,
      spend_ordered_count: 0,
      unsuppressed_count: 0,
      write_attempt_count: 0,
    };

    let write = null;
    let profile = null;
    const runNativeWrite = factory(deps, "runNativeWrite", runNativeConnectorWrite);
    let routeMinutesForProviders = null;
    const candidateAttempts = [];
    const currentCapabilityVersion = capabilityVersion(config.capabilityVersion);
    const inputCursor = resumeCursor(config.cursor);
    const outputCursor = null;
    const providerRegistry = config.providerRegistry == null ? null : config.providerRegistry;
    let providerCursor = config.providerCursor == null ? null : config.providerCursor;
    if (providerRegistry === null && providerCursor !== null) unavailable();
    if (providerRegistry !== null && !isVerifiedEventProviderRegistry(providerRegistry)) unavailable();
    const latestAttempts = latestCandidateAttempts({
      attempts: Array.isArray(config.candidateAttempts) ? config.candidateAttempts : [],
      now,
    }).latest;
    if (providerCursor && !Object.hasOwn(config, "profilePath")) {
      const createRouteMinutes = factory(deps, "createRouteMinutes", createConnectorRouteMinutes);
      routeMinutesForProviders = createRouteMinutes({
        mapsKey: requiredText(config.mapsKey),
        homeLocation: requiredText(config.homeLocation),
      });
      if (typeof routeMinutesForProviders !== "function") unavailable();
    }
    if (Object.hasOwn(config, "profilePath")) {
      const readProfile = factory(deps, "readProfile", readConnectorProfile);
      const verifyProfile = factory(deps, "isVerifiedConnectorProfile", isVerifiedConnectorProfile);
      const runLunaJudgment = factory(deps, "runLunaJudgment", buildConnectorDeterministicJudgment);
      const verifyGoalDecision = factory(
        deps, "isVerifiedEventGoalSerendipity", isVerifiedEventGoalSerendipity,
      );
      const gateDateCalendar = factory(deps, "gateDateCalendar", (...args) => pack.gateDateCalendar(...args));
      const createSpendPolicy = factory(deps, "createSpendPolicy", createEventSpendPolicy);
      const planDateSpend = factory(deps, "planDateSpend", (...args) => pack.planDateSpend(...args));
      const verifySpendSequence = factory(
        deps, "isVerifiedEventSpendSequence", isVerifiedEventSpendSequence,
      );
      const createConfirmationReader = factory(
        deps, "createConfirmationReader", createGogLumaConfirmationReader,
      );
      const createConfirmationStore = factory(
        deps, "createConfirmationStore", createLumaConfirmationMailStore,
      );
      const createTicketStore = factory(deps, "createTicketStore", createLumaTicketQrStore);
      failureCode = "CONNECTOR_NATIVE_PROFILE_FAILED";
      profile = readProfile({ tenantId, path: config.profilePath });
      if (!verifyProfile(profile) || profile.tenant_id !== tenantId || profile.timezone !== timeZone) unavailable();
      const createRouteMinutes = factory(deps, "createRouteMinutes", createConnectorRouteMinutes);
      routeMinutesForProviders = createRouteMinutes({
        mapsKey: requiredText(config.mapsKey),
        homeLocation: requiredText(config.homeLocation),
      });
      if (typeof routeMinutesForProviders !== "function") unavailable();
      const judgmentDays = dateInventory.days.filter((day) => (
        coverage.days.some((coverageDay) => coverageDay.date === day.date && coverageDay.status === "open")
        && Array.isArray(day.events) && day.events.length > 0
      ));
      if (judgmentDays.length === 0 && (!providerCursor || providerCursor.provider === "luma")) unavailable();
      const routeMinutes = routeMinutesForProviders;
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
      judgmentLoop: for (const judgmentDay of judgmentDays) {
        if (providerRegistry && providerCursor === null) {
          providerCursor = createEventProviderCursor({
            registry: providerRegistry,
            date: judgmentDay.date,
            observedAt: new Date(Date.parse(now) - 1).toISOString(),
          });
        }
        if (providerCursor && (
          providerCursor.date !== judgmentDay.date || providerCursor.provider !== "luma"
        )) continue;
        if (inputCursor && judgmentDay.date < inputCursor.date) continue;
        failureCode = "CONNECTOR_NATIVE_CALENDAR_GATE_FAILED";
        let calendarGate;
        try {
          calendarGate = await gateDateCalendar(
            dateInventory, busyInventory, judgmentDay.date, requiredText(config.homeLocation), routeMinutes,
          );
        } catch (error) {
          failureCode = calendarGateFailureCode(error);
          unavailable();
        }
        if (!calendarGate || !Array.isArray(calendarGate.candidates)) {
          failureCode = calendarGateFailureCode(null, { phase: "result" });
          unavailable();
        }
        selection.calendar_gate_event_count += calendarGate.candidates.length;
        selection.calendar_eligible_count += calendarGate.candidates.filter(
          (candidate) => candidate && candidate.eligible === true,
        ).length;
        if (!calendarGate.candidates.some((candidate) => candidate && candidate.eligible === true)) {
          if (providerCursor) {
            providerCursor = advanceEventProviderCursor({
              cursor: providerCursor,
              registry: providerRegistry,
              transition: "provider_exhausted",
              observedAt: nextCursorInstant(providerCursor, now),
            });
            break judgmentLoop;
          }
          continue;
        }
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
        selection.luna_ranked_count += goalDecision.ranked_events.length;
        failureCode = "CONNECTOR_NATIVE_SPEND_GATE_FAILED";
        const spendSequence = await planDateSpend(policy, dateInventory, calendarGate, goalDecision);
        if (!verifySpendSequence(spendSequence)) unavailable();
        selection.spend_ordered_count += spendSequence.ordered_candidates.length;
        let resumableCandidates = spendSequence.ordered_candidates;
        if (inputCursor && judgmentDay.date === inputCursor.date) {
          const cursorIndex = resumableCandidates.findIndex(
            (candidate) => candidate.event_ref === inputCursor.event_ref,
          );
          if (cursorIndex >= 0) resumableCandidates = resumableCandidates.slice(cursorIndex + 1);
        }
        const orderedCandidates = resumableCandidates;
        selection.unsuppressed_count += orderedCandidates.length;
        if (orderedCandidates.length === 0) {
          if (providerCursor) {
            providerCursor = advanceEventProviderCursor({
              cursor: providerCursor,
              registry: providerRegistry,
              transition: "provider_exhausted",
              observedAt: nextCursorInstant(providerCursor, now),
            });
            break judgmentLoop;
          }
          continue;
        }
        failureCode = "CONNECTOR_NATIVE_WRITE_FAILED";
        let providerHasUnknownEffect = false;
        let providerVerifiedSuccess = false;
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
                ...(currentCapabilityVersion ? { capability_version: currentCapabilityVersion } : {}),
              }));
              if (proof.state !== "absent") {
                providerHasUnknownEffect = true;
                continue;
              }
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
          selection.write_attempt_count += 1;
          const candidateOutcome = classifyConnectorCandidateOutcome(write);
          candidateAttempts.push(Object.freeze({
            event_ref: candidateOutcome.event_ref,
            outcome: candidateOutcome.classification,
            safe_reason: candidateOutcome.error_code || write.outcome,
            observed_at: now,
            retry_after: null,
            ...(currentCapabilityVersion ? { capability_version: currentCapabilityVersion } : {}),
          }));
          if (candidateOutcome.classification === "verified_success") {
            providerVerifiedSuccess = true;
            break judgmentLoop;
          }
          if (candidateOutcome.classification === "unknown_effect") providerHasUnknownEffect = true;
          if (providerCursor && candidateOutcome.classification === "known_no_effect") {
            providerCursor = advanceEventProviderCursor({
              cursor: providerCursor,
              registry: providerRegistry,
              transition: "known_no_effect",
              observedAt: nextCursorInstant(providerCursor, now),
            });
          }
        }
        if (providerCursor && !providerVerifiedSuccess && !providerHasUnknownEffect) {
          providerCursor = advanceEventProviderCursor({
            cursor: providerCursor,
            registry: providerRegistry,
            transition: "provider_exhausted",
            observedAt: nextCursorInstant(providerCursor, now),
          });
          break judgmentLoop;
        }
      }
    }

    let providerDiscovery = null;
    let providerDateInventory = null;
    if (providerCursor && providerCursor.provider === "connpass") {
      if (typeof pack.discoverConnpassDate !== "function") unavailable();
      failureCode = "CONNECTOR_NATIVE_PROVIDER_DISCOVERY_FAILED";
      let handoff;
      try {
        handoff = await pack.discoverConnpassDate(providerCursor.date, { timeZone });
      } catch {
        handoff = buildConnpassBrowserHandoff({
          date: providerCursor.date,
          candidates: [],
          browserPageCount: 0,
        });
      }
      const verifyHandoff = factory(
        deps, "isVerifiedEventSourceHandoff", isVerifiedEventSourceHandoff,
      );
      if (
        !verifyHandoff(handoff)
        || handoff.coverage_status !== "open"
        || handoff.coverage_credit_count !== 0
        || !Array.isArray(handoff.advisory_candidates)
      ) unavailable();
      providerDiscovery = Object.freeze({
        provider: "connpass",
        date: providerCursor.date,
        status: handoff.status,
        coverage_status: "open",
        coverage_credit_count: 0,
        network_call_count: handoff.network_call_count,
        browser_page_count: handoff.browser_page_count,
        advisory_candidates: Object.freeze([...handoff.advisory_candidates]),
      });
      if (handoff.status === "authorized_source_empty") {
        providerCursor = advanceEventProviderCursor({
          cursor: providerCursor,
          registry: providerRegistry,
          transition: "provider_exhausted",
          observedAt: nextCursorInstant(providerCursor, now),
        });
      }
      if (handoff.status === "advisory_candidates_found") {
        if (typeof routeMinutesForProviders !== "function") unavailable();
        const gateConnpass = factory(
          deps, "gateConnpassCalendar", evaluateConnpassCalendarCandidateGate,
        );
        const verifyCalendarGate = factory(
          deps, "isVerifiedCalendarCandidateGate", isVerifiedCalendarCandidateGate,
        );
        const selectConnpass = factory(
          deps, "selectCalendarEligibleConnpass", calendarEligibleConnpassCandidates,
        );
        const calendarGate = await gateConnpass({
          handoff, busyInventory, homeLocation: requiredText(config.homeLocation),
          routeMinutes: routeMinutesForProviders,
        });
        if (!verifyCalendarGate(calendarGate)) unavailable();
        const eligible = selectConnpass(handoff, calendarGate);
        if (!Array.isArray(eligible)) unavailable();
        providerDiscovery = Object.freeze({
          ...providerDiscovery,
          calendar_gate_status: calendarGate.status,
          advisory_candidates: Object.freeze([...eligible]),
        });
        if (calendarGate.status === "evaluated" && eligible.length > 0) {
          const buildProviderInventory = factory(
            deps, "buildEventProviderDateInventory", buildEventProviderDateInventory,
          );
          providerDateInventory = buildProviderInventory({
            coverage, handoff, eligibleCandidates: eligible, now,
          });
          if (!providerDateInventory || providerDateInventory.provider !== "connpass") unavailable();

          if (!profile) unavailable();
          const createProviderEvidence = factory(
            deps, "createConnpassEvidenceStore", createConnpassEvidenceStore,
          );
          const createProvider = factory(deps, "createConnpassProvider", createConnpassBrowserProvider);
          const providerEvidence = createProviderEvidence({ dataDir: evidenceDir });
          if (
            !providerEvidence || typeof providerEvidence.record !== "function"
            || typeof providerEvidence.readExternalReceipt !== "function"
            || typeof providerEvidence.readArtifact !== "function"
          ) unavailable();
          const connpassProvider = createProvider({
            dailyDriver, evidenceStore: providerEvidence, now: () => now,
          });
          if (
            !connpassProvider || typeof connpassProvider.inspectRegistration !== "function"
            || typeof connpassProvider.submitRegistration !== "function"
          ) unavailable();
          const providerEvents = providerDateInventory.days
            .flatMap((day) => day.events || []).slice(providerCursor.candidate_index);
          let providerHasUnknownEffect = false;
          let providerVerifiedSuccess = false;
          for (const selectedEvent of providerEvents) {
            failureCode = "CONNECTOR_NATIVE_WRITE_FAILED";
            write = await runNativeWrite({
              application: {
                tenantId,
                eventRef: selectedEvent.event_ref,
                eventUrl: selectedEvent.canonical_url,
                eventStartIso: selectedEvent.starts_at,
                identityRef: profile.identity_ref,
                browserProfileRef: profile.browser_profile_ref,
                calendarRef: profile.calendar_ref,
              },
              profile,
              dateInventory: providerDateInventory,
              currentCoverage: coverage,
              busyInventory,
              calendar,
              calendarId: requiredText(config.calendarId),
              telegramTarget: requiredText(config.telegramTarget),
              calendarCoverageUrl: requiredText(config.calendarCoverageUrl),
              registrationIdentity: requiredText(config.lumaName),
              now,
            }, {
              provider: connpassProvider,
              readExternalReceipt: providerEvidence.readExternalReceipt,
              readArtifact: providerEvidence.readArtifact,
              buildEventApplicationJob: factory(
                deps, "buildConnpassEventApplicationJob", buildConnpassEventApplicationJob,
              ),
              executeLumaRsvpJob: factory(
                deps, "executeConnpassRsvpJob", executeConnpassRsvpJob,
              ),
              fetchImpl: globalThis.fetch,
              ...(deps.writeDependencies || {}),
            });
            selection.write_attempt_count += 1;
            const candidateOutcome = classifyConnectorCandidateOutcome(write);
            candidateAttempts.push(Object.freeze({
              event_ref: candidateOutcome.event_ref,
              outcome: candidateOutcome.classification,
              safe_reason: candidateOutcome.error_code || write.outcome,
              observed_at: now,
              retry_after: null,
              ...(currentCapabilityVersion ? { capability_version: currentCapabilityVersion } : {}),
            }));
            if (candidateOutcome.classification === "verified_success") {
              providerVerifiedSuccess = true;
              break;
            }
            if (["unknown_effect", "recovery_required"].includes(candidateOutcome.classification)) {
              providerHasUnknownEffect = true;
              break;
            }
            providerCursor = advanceEventProviderCursor({
              cursor: providerCursor, registry: providerRegistry,
              transition: "known_no_effect", observedAt: nextCursorInstant(providerCursor, now),
            });
          }
          if (!providerVerifiedSuccess && !providerHasUnknownEffect) {
            providerCursor = advanceEventProviderCursor({
              cursor: providerCursor, registry: providerRegistry,
              transition: "provider_exhausted", observedAt: nextCursorInstant(providerCursor, now),
            });
          }
        }
        if (calendarGate.status === "evaluated" && eligible.length === 0) {
          providerCursor = advanceEventProviderCursor({
            cursor: providerCursor, registry: providerRegistry,
            transition: "provider_exhausted", observedAt: nextCursorInstant(providerCursor, now),
          });
        }
      }
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
      selection: Object.freeze({ ...selection }),
      calendar: Object.freeze({
        transport: "gog",
        all_calendars_read: true,
        calendar_count: busyInventory.calendar_count,
        busy_event_count: busyInventory.busy_event_count,
      }),
      candidate,
      provider_discovery: providerDiscovery,
      provider_inventory: providerDateInventory,
      write,
      candidate_attempts: Object.freeze([...candidateAttempts]),
      cursor: outputCursor,
      provider_cursor: providerCursor,
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

module.exports = { calendarGateFailureCode, runNativeConnectorPass };
