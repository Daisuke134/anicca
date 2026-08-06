"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  runNativeConnectorPass,
} = require("./connector-native-runtime.js");
const { DAILY_DRIVER_CDP } = require("./cloakbrowser-daily-driver.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { planConnectorCoverageContinuation } = require("./connector-coverage-continuation.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");

const NOW = "2026-08-02T01:00:00.000Z";
const TENANT = "dais-local";

function coverage() {
  return buildRollingEventCoverage({
    tenantId: TENANT,
    timeZone: "Asia/Tokyo",
    now: NOW,
    resolvedDays: [],
  });
}

async function dateInventory(currentCoverage, options = {}) {
  const agentStartsAt = options.agentStartsAt || "2026-08-05T14:00:00+09:00";
  const agentEndsAt = options.agentEndsAt || "2026-08-05T15:00:00+09:00";
  let round = 0;
  const discovered = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [{
      href: "https://luma.com/founder-night",
      title: "Founder Night",
      cardText: "Founder Night",
      timelineText: "Aug 5",
    }, {
      href: "https://luma.com/agent-night",
      title: "Agent Night",
      cardText: "Agent Night",
      timelineText: "Aug 5",
    }] : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
  const detail = normalizeLumaEventDetail({
    canonicalUrl: "https://luma.com/founder-night",
    jsonLd: [{
      "@type": "Event",
      name: "Founder Night",
      description: "public description only",
      startDate: "2026-08-05T12:00:00+09:00",
      endDate: "2026-08-05T13:00:00+09:00",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
    }],
    controls: ["Register"],
  });
  const secondDetail = normalizeLumaEventDetail({
    canonicalUrl: "https://luma.com/agent-night",
    jsonLd: [{
      "@type": "Event",
      name: "Agent Night",
      description: "public description only",
      startDate: agentStartsAt,
      endDate: agentEndsAt,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
    }],
    controls: ["Register"],
  });
  return buildLumaDateInventory({
    coverage: currentCoverage,
    inventory: discovered,
    details: [detail, secondDetail],
    now: NOW,
  });
}

async function busyInventory() {
  return inspectGoogleCalendarBusyInventory({
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() { return []; },
    },
    timeMin: "2026-08-01T15:00:00.000Z",
    timeMax: "2026-08-22T15:00:00.000Z",
    timeZone: "Asia/Tokyo",
    now: NOW,
  });
}

async function fixture(options = {}) {
  const currentCoverage = coverage();
  const inventory = await dateInventory(currentCoverage, options);
  const busy = await busyInventory();
  const calls = [];
  const dailyDriver = { async withLumaPage() { throw new Error("test auth controls this seam"); } };
  const auth = {
    async ensureAuthenticated() {
      calls.push(["auth"]);
      return Object.freeze({ status: "authenticated", recovered: false });
    },
  };
  const calendar = {
    kind: "gog",
    ready() { return true; },
  };
  const pack = {
    provider: {
      async inspectRegistration() { return { state: "registered" }; },
      async submitRegistration() { throw new Error("registration must stay deferred"); },
    },
    async readDateInventory(receivedCoverage, options) {
      calls.push(["date-inventory", receivedCoverage, options]);
      return receivedCoverage.coverage_snapshot_id === currentCoverage.coverage_snapshot_id
        ? inventory
        : dateInventory(receivedCoverage, options);
    },
    async inspectEvent() {
      calls.push(["restore-event"]);
      return normalizeLumaEventDetail({
        canonicalUrl: "https://luma.com/founder-night",
        jsonLd: [{
          "@type": "Event", name: "Founder Night", description: "public description only",
          startDate: "2026-08-05T12:00:00+09:00", endDate: "2026-08-05T13:00:00+09:00",
          eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
          eventStatus: "https://schema.org/EventScheduled",
          location: { name: "Shibuya Hall", address: "Shibuya, Tokyo" },
        }], controls: ["Register"],
      });
    },
    async readBusyCalendar(receivedCalendar, options) {
      calls.push(["busy-calendar", receivedCalendar, options]);
      return busy;
    },
    async runSameDayCandidates(candidates, attempt) {
      calls.push(["candidate-sequence", candidates]);
      return runLumaCandidateSequence({ candidates, attempt });
    },
    planCoverageContinuation(receivedCoverage, observedOutcomes, now) {
      calls.push(["continuation", receivedCoverage, observedOutcomes, now]);
      return planConnectorCoverageContinuation({
        coverage: receivedCoverage,
        observedOutcomes,
        now,
      });
    },
    async syncRegistrationCalendar() { throw new Error("calendar sync must stay deferred"); },
    async deliverCoverageTelegram() { throw new Error("Telegram must stay deferred"); },
    async captureLumaTicketQr() { return "verified-ticket"; },
  };
  return {
    calls,
    pack,
    config: {
      tenantId: TENANT,
      timeZone: "Asia/Tokyo",
      now: NOW,
      evidenceDir: "/tmp/connector-native-runtime-evidence",
      calendarAccount: "dais@example.test",
      lumaEmail: "dais@example.com",
      lumaName: "Dais Example",
      gogKeyring: "fixture-keyring",
      gogBin: undefined,
    },
    deps: {
      createDailyDriver(input) {
        calls.push(["create-daily-driver", input]);
        return dailyDriver;
      },
      createAuth(input) {
        calls.push(["create-auth", input]);
        return auth;
      },
      createEvidenceStore(input) {
        calls.push(["create-evidence-store", input]);
        return {
          async record() { throw new Error("evidence write must stay deferred"); },
          async readExternalReceipt() {},
          async readArtifact() {},
        };
      },
      createCalendar(input) {
        calls.push(["create-calendar", input]);
        return calendar;
      },
      createPack(input) {
        calls.push(["create-pack", input]);
        return pack;
      },
      createConfirmationReader() { return async () => ({ id: "mail-1" }); },
      createConfirmationStore() { return { record: async () => ({}) }; },
      createTicketStore() {
        return { record: async () => ({}), readArtifact: async () => Buffer.from("fixture") };
      },
    },
  };
}

test("the native runtime composes one shared daily driver, all-calendar gog, and a bounded incomplete continuation", async () => {
  const input = await fixture();
  const result = await runNativeConnectorPass(input);

  assert.equal(result.status, "incomplete");
  assert.equal(result.coverage.counts.open, 21);
  assert.equal(result.inventory.complete, true);
  assert.deepEqual(result.calendar, {
    transport: "gog",
    all_calendars_read: true,
    calendar_count: 1,
    busy_event_count: 0,
  });
  assert.deepEqual(result.continuation, {
    status: "continue",
    open_date_count: 21,
    next_action: "refresh_inventory",
  });
  assert.deepEqual(result.deferred_effects, {
    registration: "not_executed",
    receipt_verification: "not_executed",
    calendar_sync: "not_executed",
    telegram_delivery: "not_executed",
  });
  assert.equal(JSON.stringify(result).includes("public description only"), false);
  assert.deepEqual(input.calls.map((call) => call[0]), [
    "create-daily-driver",
    "create-auth",
    "create-evidence-store",
    "create-calendar",
    "create-pack",
    "auth",
    "date-inventory",
    "busy-calendar",
    "continuation",
  ]);
  assert.equal(input.calls[0][1].endpoint, DAILY_DRIVER_CDP);
  assert.equal(input.calls[1][1].dailyDriver, input.calls[4][1].dailyDriver);
  assert.equal(input.calls[7][2].timeMin, "2026-08-01T15:00:00.000Z");
  assert.equal(input.calls[7][2].timeMax, "2026-08-22T15:00:00.000Z");
});

test("a candidate failure remains incomplete and defers every write boundary", async () => {
  const input = await fixture();
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      candidates: [{
        event_ref: "luma-event://event/founder-night",
        canonical_url: "https://luma.com/founder-night",
      }],
      attemptCandidate: async () => ({ status: "full" }),
    },
  });

  assert.equal(result.status, "incomplete");
  assert.equal(result.coverage.counts.open, 21);
  assert.deepEqual(result.candidate, {
    status: "next_provider_required",
    outcome: "search_exhausted",
  });
  assert.deepEqual(result.continuation, {
    status: "continue",
    open_date_count: 21,
    next_action: "refresh_inventory",
  });
  assert.equal(input.calls.filter((call) => call[0] === "candidate-sequence").length, 1);
  assert.equal(input.calls.some((call) => call[0] === "calendar-sync"), false);
  assert.equal(input.calls.some((call) => call[0] === "telegram"), false);
});

test("verified delivery history restores its Luma date as covered before inventory refresh", async () => {
  const input = await fixture();
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      deliveredReceipts: [{
        event_ref: "luma-event://event/founder-night",
        calendar_event_ref: `calendar-evidence://google/event/${"a".repeat(64)}`,
        telegram_provider_id: "7372",
      }],
    },
  });

  assert.equal(result.coverage.counts.covered_new, 1);
  assert.equal(result.coverage.counts.open, 20);
  assert.equal(input.calls.some(([name]) => name === "restore-event"), true);
  assert.equal(input.calls.find(([name]) => name === "date-inventory")[1].counts.covered_new, 1);
});

test("configured native execution gates the date then uses Luna and passes one verified candidate to the write pipeline", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [{
    event_ref: "luma-event://event/founder-night",
    goal_fit: "strong",
    goal_reason: "grounded",
    serendipity_reason: "grounded",
  }] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }],
    skipped: [],
  });
  const writeResult = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/founder-night",
  });
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
      lumaEmail: "dais@example.com",
      lumaName: "Dais Example",
      gogKeyring: "fixture-keyring",
      gogBin: "/fixture/gog",
    },
    deps: {
      ...input.deps,
      readProfile(value) { input.calls.push(["profile", value]); return profile; },
      async runLunaJudgment(value) { input.calls.push(["luna", value]); return goalDecision; },
      async gateDateCalendar(...value) {
        input.calls.push(["gate", ...value]);
        return Object.freeze({ date: "2026-08-05", candidates: [{ event_ref: "luma-event://event/founder-night", eligible: true }] });
      },
      async createSpendPolicy(value) { input.calls.push(["policy", value]); return Object.freeze({ limits: [] }); },
      planDateSpend(...value) { input.calls.push(["spend", ...value]); return spendSequence; },
      async runNativeWrite(value, dependencies) { input.calls.push(["write", value, dependencies]); return writeResult; },
      createConfirmationReader(value) {
        input.calls.push(["confirmation-reader", value]);
        return async () => ({ id: "mail-1" });
      },
      createConfirmationStore(value) {
        input.calls.push(["confirmation-store", value]);
        return { record: async () => ({ external_receipt_ref: "gmail-message://fixture" }) };
      },
      createTicketStore(value) {
        input.calls.push(["ticket-store", value]);
        return {
          record: async () => ({ ticket_receipt_ref: "ticket://fixture", artifact_ref: "object://fixture" }),
          readArtifact: async () => Buffer.from("fixture"),
        };
      },
      createRouteMinutes(value) {
        input.calls.push(["route-adapter", value]);
        return async () => 20;
      },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
      isVerifiedEventSpendSequence: (value) => value === spendSequence,
    },
  });

  assert.equal(result.write, writeResult);
  assert.deepEqual(input.calls.filter(([name]) => ["profile", "luna", "route-adapter", "gate", "policy", "spend", "write"].includes(name))
    .map(([name]) => name), ["profile", "route-adapter", "policy", "gate", "luna", "spend", "write"]);
  const writeInput = input.calls.find(([name]) => name === "write")[1];
  const writeDependencies = input.calls.find(([name]) => name === "write")[2];
  assert.equal(writeInput.application.eventRef, "luma-event://event/founder-night");
  assert.equal(writeInput.goalDecision, goalDecision);
  assert.equal(typeof writeDependencies.provider.inspectRegistration, "function");
  assert.equal(typeof writeDependencies.readExternalReceipt, "function");
  assert.equal(typeof writeDependencies.readArtifact, "function");
  assert.equal(typeof writeDependencies.fetchImpl, "function");
  assert.equal(typeof writeDependencies.readLumaConfirmation, "function");
  assert.equal(typeof writeDependencies.recordLumaConfirmation, "function");
  assert.equal(typeof writeDependencies.captureLumaTicketQr, "function");
  assert.equal(typeof writeDependencies.recordLumaTicketQr, "function");
  assert.equal(typeof writeDependencies.readTicketArtifact, "function");
  assert.equal(writeInput.registrationIdentity, "Dais Example");
  assert.equal(input.calls.find(([name]) => name === "luna")[1].date, "2026-08-05");
});

test("a known missing Luma form answer skips to the next ranked candidate", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [
    { event_ref: "luma-event://event/founder-night" },
    { event_ref: "luma-event://event/agent-night" },
  ] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }, {
      event_ref: "luma-event://event/agent-night",
      canonical_url: "https://luma.com/agent-night",
    }],
    skipped: [],
  });
  const delivered = Object.freeze({ status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/agent-night" });
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
    },
    deps: {
      ...input.deps,
      readProfile() { return profile; },
      async runLunaJudgment() { return goalDecision; },
      async gateDateCalendar() {
        return Object.freeze({ date: "2026-08-05", candidates: spendSequence.ordered_candidates.map(({ event_ref }) => ({ event_ref, eligible: true })) });
      },
      async createSpendPolicy() { return Object.freeze({ limits: [] }); },
      planDateSpend() { return spendSequence; },
      async runNativeWrite(value) {
        input.calls.push(["write", value]);
        return value.application.eventRef.endsWith("founder-night")
          ? Object.freeze({
            status: "incomplete",
            outcome: "application_failed",
            error_code: "LUMA_FORM_INPUT_REQUIRED",
            event_ref: "luma-event://event/founder-night",
          })
          : delivered;
      },
      createRouteMinutes() { return async () => 20; },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
      isVerifiedEventSpendSequence: (value) => value === spendSequence,
    },
  });

  assert.equal(result.write, delivered);
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/founder-night",
    "luma-event://event/agent-night",
  ]);
});

test("a known unavailable Luma RSVP skips to the next ranked candidate", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [
    { event_ref: "luma-event://event/founder-night" },
    { event_ref: "luma-event://event/agent-night" },
  ] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }, {
      event_ref: "luma-event://event/agent-night",
      canonical_url: "https://luma.com/agent-night",
    }],
    skipped: [],
  });
  const delivered = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/agent-night",
  });
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
    },
    deps: {
      ...input.deps,
      readProfile() { return profile; },
      async runLunaJudgment() { return goalDecision; },
      async gateDateCalendar() {
        return Object.freeze({
          date: "2026-08-05",
          candidates: spendSequence.ordered_candidates.map(({ event_ref }) => ({ event_ref, eligible: true })),
        });
      },
      async createSpendPolicy() { return Object.freeze({ limits: [] }); },
      planDateSpend() { return spendSequence; },
      async runNativeWrite(value) {
        input.calls.push(["write", value]);
        return value.application.eventRef.endsWith("founder-night")
          ? Object.freeze({
            status: "incomplete",
            outcome: "application_failed",
            error_code: "LUMA_RSVP_UNAVAILABLE",
            event_ref: "luma-event://event/founder-night",
          })
          : delivered;
      },
      createRouteMinutes() { return async () => 20; },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
      isVerifiedEventSpendSequence: (value) => value === spendSequence,
    },
  });

  assert.equal(result.write, delivered);
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/founder-night",
    "luma-event://event/agent-night",
  ]);
  assert.deepEqual(result.candidate_attempts, [{
    event_ref: "luma-event://event/founder-night",
    outcome: "known_no_effect",
    safe_reason: "LUMA_RSVP_UNAVAILABLE",
    observed_at: NOW,
    retry_after: null,
  }, {
    event_ref: "luma-event://event/agent-night",
    outcome: "verified_success",
    safe_reason: "open_coverage",
    observed_at: NOW,
    retry_after: null,
  }]);
});

test("a terminal known failure from the previous wake is not written again", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [
    { event_ref: "luma-event://event/founder-night" },
    { event_ref: "luma-event://event/agent-night" },
  ] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }, {
      event_ref: "luma-event://event/agent-night",
      canonical_url: "https://luma.com/agent-night",
    }],
    skipped: [],
  });
  const delivered = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/agent-night",
  });
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
      candidateAttempts: [{
        event_ref: "luma-event://event/founder-night",
        outcome: "known_no_effect",
        safe_reason: "LUMA_RSVP_UNAVAILABLE",
        observed_at: "2026-08-02T00:00:00.000Z",
        retry_after: null,
      }],
    },
    deps: {
      ...input.deps,
      readProfile() { return profile; },
      async runLunaJudgment() { return goalDecision; },
      async gateDateCalendar() {
        return Object.freeze({
          date: "2026-08-05",
          candidates: spendSequence.ordered_candidates.map(({ event_ref }) => ({ event_ref, eligible: true })),
        });
      },
      async createSpendPolicy() { return Object.freeze({ limits: [] }); },
      planDateSpend() { return spendSequence; },
      async runNativeWrite(value) {
        input.calls.push(["write", value]);
        if (value.application.eventRef.endsWith("founder-night")) throw new Error("suppressed event was written again");
        return delivered;
      },
      createRouteMinutes() { return async () => 20; },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
      isVerifiedEventSpendSequence: (value) => value === spendSequence,
    },
  });

  assert.equal(result.write, delivered);
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/agent-night",
  ]);
});

test("an unknown effect is read back before absent retry or registered verification", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [{
    event_ref: "luma-event://event/founder-night",
  }] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }],
    skipped: [],
  });
  let inspections = 0;
  let writes = 0;
  let providerState = "unknown";
  const delivered = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/founder-night",
  });
  input.deps.createPack = () => ({
    ...input.pack,
    provider: {
      async inspectRegistration(contract) {
        inspections += 1;
        assert.equal(contract.event_ref, "luma-event://event/founder-night");
        assert.equal(contract.canonical_url, "https://luma.com/founder-night");
        return { state: providerState };
      },
      async submitRegistration() { throw new Error("unknown effect was resubmitted"); },
    },
    async gateDateCalendar() {
      return Object.freeze({ date: "2026-08-05", candidates: [{
        event_ref: "luma-event://event/founder-night", eligible: true,
      }] });
    },
  });
  const wake = () => runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
      candidateAttempts: [{
        event_ref: "luma-event://event/founder-night",
        outcome: "unknown_effect",
        safe_reason: "CONNECTOR_EFFECT_UNKNOWN",
        observed_at: "2026-08-02T00:00:00.000Z",
        retry_after: null,
      }],
    },
    deps: {
      ...input.deps,
      readProfile() { return profile; },
      async runLunaJudgment() { return goalDecision; },
      async createSpendPolicy() { return Object.freeze({ limits: [] }); },
      planDateSpend() { return spendSequence; },
      async runNativeWrite() { writes += 1; return delivered; },
      createRouteMinutes() { return async () => 20; },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
      isVerifiedEventSpendSequence: (value) => value === spendSequence,
    },
  });

  const result = await wake();
  assert.equal(inspections, 1);
  assert.equal(writes, 0);
  assert.equal(result.write, null);
  assert.deepEqual(result.candidate_attempts, [{
    event_ref: "luma-event://event/founder-night",
    outcome: "unknown_effect",
    safe_reason: "CONNECTOR_EFFECT_UNKNOWN",
    observed_at: NOW,
    retry_after: null,
  }]);

  providerState = "absent";
  const absent = await wake();
  assert.equal(writes, 0);
  assert.deepEqual(absent.candidate_attempts, [{
    event_ref: "luma-event://event/founder-night",
    outcome: "known_no_effect",
    safe_reason: "LUMA_RECONCILED_ABSENT",
    observed_at: NOW,
    retry_after: NOW,
  }]);

  providerState = "registered";
  const registered = await wake();
  assert.equal(writes, 1);
  assert.equal(registered.write, delivered);
});

test("known failures exhausting one date continue to the next open date in the same pass", async () => {
  const input = await fixture({
    agentStartsAt: "2026-08-06T14:00:00+09:00",
    agentEndsAt: "2026-08-06T15:00:00+09:00",
  });
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const decisions = {
    "2026-08-05": Object.freeze({ ranked_events: [{ event_ref: "luma-event://event/founder-night" }] }),
    "2026-08-06": Object.freeze({ ranked_events: [{ event_ref: "luma-event://event/agent-night" }] }),
  };
  const sequences = {
    "luma-event://event/founder-night": Object.freeze({
      ordered_candidates: [{
        event_ref: "luma-event://event/founder-night",
        canonical_url: "https://luma.com/founder-night",
      }],
      skipped: [],
    }),
    "luma-event://event/agent-night": Object.freeze({
      ordered_candidates: [{
        event_ref: "luma-event://event/agent-night",
        canonical_url: "https://luma.com/agent-night",
      }],
      skipped: [],
    }),
  };
  const delivered = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/agent-night",
  });
  const result = await runNativeConnectorPass({
    ...input,
    config: {
      ...input.config,
      profilePath: "/private/tmp/dais-local.json",
      lunaEvidenceDir: "/private/tmp/connector-luna",
      homeLocation: "opaque-home",
      telegramTarget: "opaque-chat",
      calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
      calendarId: "primary",
      mapsKey: "maps-secret",
    },
    deps: {
      ...input.deps,
      readProfile() { return profile; },
      async runLunaJudgment(value) { return decisions[value.date]; },
      async gateDateCalendar(_dateInventory, _busyInventory, date) {
        const eventRef = date === "2026-08-05"
          ? "luma-event://event/founder-night"
          : "luma-event://event/agent-night";
        return Object.freeze({ date, candidates: [{ event_ref: eventRef, eligible: true }] });
      },
      async createSpendPolicy() { return Object.freeze({ limits: [] }); },
      planDateSpend(_policy, _inventory, _gate, decision) {
        return sequences[decision.ranked_events[0].event_ref];
      },
      async runNativeWrite(value) {
        input.calls.push(["write", value]);
        return value.application.eventRef.endsWith("founder-night")
          ? Object.freeze({
            status: "incomplete",
            outcome: "application_failed",
            error_code: "LUMA_RSVP_UNAVAILABLE",
            event_ref: "luma-event://event/founder-night",
          })
          : delivered;
      },
      createRouteMinutes() { return async () => 20; },
      isVerifiedConnectorProfile: (value) => value === profile,
      isVerifiedEventGoalSerendipity: (value) => Object.values(decisions).includes(value),
      isVerifiedEventSpendSequence: (value) => Object.values(sequences).includes(value),
    },
  });

  assert.equal(result.write, delivered);
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/founder-night",
    "luma-event://event/agent-night",
  ]);
});

test("candidate budget returns a cursor and the next wake resumes after that candidate", async () => {
  const input = await fixture();
  const profile = Object.freeze({ tenant_id: TENANT, timezone: "Asia/Tokyo" });
  const goalDecision = Object.freeze({ ranked_events: [
    { event_ref: "luma-event://event/founder-night" },
    { event_ref: "luma-event://event/agent-night" },
  ] });
  const spendSequence = Object.freeze({
    ordered_candidates: [{
      event_ref: "luma-event://event/founder-night",
      canonical_url: "https://luma.com/founder-night",
    }, {
      event_ref: "luma-event://event/agent-night",
      canonical_url: "https://luma.com/agent-night",
    }],
    skipped: [],
  });
  const delivered = Object.freeze({
    status: "incomplete",
    outcome: "open_coverage",
    event_ref: "luma-event://event/agent-night",
  });
  const dependencies = {
    ...input.deps,
    readProfile() { return profile; },
    async runLunaJudgment() { return goalDecision; },
    async gateDateCalendar() {
      return Object.freeze({
        date: "2026-08-05",
        candidates: spendSequence.ordered_candidates.map(({ event_ref }) => ({ event_ref, eligible: true })),
      });
    },
    async createSpendPolicy() { return Object.freeze({ limits: [] }); },
    planDateSpend() { return spendSequence; },
    async runNativeWrite(value) {
      input.calls.push(["write", value]);
      return value.application.eventRef.endsWith("founder-night")
        ? Object.freeze({
          status: "incomplete",
          outcome: "application_failed",
          error_code: "LUMA_RSVP_UNAVAILABLE",
          event_ref: "luma-event://event/founder-night",
        })
        : delivered;
    },
    createRouteMinutes() { return async () => 20; },
    isVerifiedConnectorProfile: (value) => value === profile,
    isVerifiedEventGoalSerendipity: (value) => value === goalDecision,
    isVerifiedEventSpendSequence: (value) => value === spendSequence,
  };
  const baseConfig = {
    ...input.config,
    profilePath: "/private/tmp/dais-local.json",
    lunaEvidenceDir: "/private/tmp/connector-luna",
    homeLocation: "opaque-home",
    telegramTarget: "opaque-chat",
    calendarCoverageUrl: "https://calendar.google.com/calendar/u/0/r",
    calendarId: "primary",
    mapsKey: "maps-secret",
    passCandidateBudget: 1,
  };

  const first = await runNativeConnectorPass({ ...input, config: baseConfig, deps: dependencies });
  assert.deepEqual(first.cursor, {
    status: "resume_after",
    date: "2026-08-05",
    event_ref: "luma-event://event/founder-night",
    observed_at: NOW,
  });
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/founder-night",
  ]);

  input.calls.length = 0;
  const second = await runNativeConnectorPass({
    ...input,
    config: { ...baseConfig, cursor: first.cursor },
    deps: {
      ...dependencies,
      async runNativeWrite(value) {
        input.calls.push(["write", value]);
        if (value.application.eventRef.endsWith("founder-night")) throw new Error("cursor did not advance");
        return delivered;
      },
    },
  });
  assert.equal(second.write, delivered);
  assert.equal(second.cursor, null);
  assert.deepEqual(input.calls.filter(([name]) => name === "write").map(([, value]) => value.application.eventRef), [
    "luma-event://event/agent-night",
  ]);
});

test("native runtime exposes only its bounded failing stage", async () => {
  const input = await fixture();
  input.deps.createAuth = () => ({ async ensureAuthenticated() { throw new Error("raw cookie leak"); } });
  await assert.rejects(runNativeConnectorPass(input), (error) => {
    assert.equal(error.message, "Connector native runtime unavailable");
    assert.equal(error.code, "CONNECTOR_NATIVE_AUTH_FAILED");
    assert.equal(String(error).includes("cookie"), false);
    return true;
  });
});
