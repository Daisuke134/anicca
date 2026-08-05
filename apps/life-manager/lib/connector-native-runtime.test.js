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

async function dateInventory(currentCoverage) {
  let round = 0;
  const discovered = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [{
      href: "https://luma.com/founder-night",
      title: "Founder Night",
      cardText: "Founder Night",
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
  return buildLumaDateInventory({
    coverage: currentCoverage,
    inventory: discovered,
    details: [detail],
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

async function fixture() {
  const currentCoverage = coverage();
  const inventory = await dateInventory(currentCoverage);
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
      async submitRegistration() { throw new Error("registration must stay deferred"); },
    },
    async readDateInventory(receivedCoverage, options) {
      calls.push(["date-inventory", receivedCoverage, options]);
      return inventory;
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
  };
  return {
    calls,
    config: {
      tenantId: TENANT,
      timeZone: "Asia/Tokyo",
      now: NOW,
      evidenceDir: "/tmp/connector-native-runtime-evidence",
      calendarAccount: "dais@example.test",
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
        return { async record() { throw new Error("evidence write must stay deferred"); } };
      },
      createCalendar(input) {
        calls.push(["create-calendar", input]);
        return calendar;
      },
      createPack(input) {
        calls.push(["create-pack", input]);
        return pack;
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

test("configured native execution uses Luna then passes one verified candidate to the write pipeline", async () => {
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
  const writeResult = Object.freeze({ status: "incomplete", outcome: "open_coverage" });
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
      readProfile(value) { input.calls.push(["profile", value]); return profile; },
      async runLunaJudgment(value) { input.calls.push(["luna", value]); return goalDecision; },
      async gateDateCalendar(...value) { input.calls.push(["gate", ...value]); return Object.freeze({ date: "2026-08-05" }); },
      async createSpendPolicy(value) { input.calls.push(["policy", value]); return Object.freeze({ limits: [] }); },
      planDateSpend(...value) { input.calls.push(["spend", ...value]); return spendSequence; },
      async runNativeWrite(value) { input.calls.push(["write", value]); return writeResult; },
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
    .map(([name]) => name), ["profile", "luna", "route-adapter", "gate", "policy", "spend", "write"]);
  const writeInput = input.calls.find(([name]) => name === "write")[1];
  assert.equal(writeInput.application.eventRef, "luma-event://event/founder-night");
  assert.equal(writeInput.goalDecision, goalDecision);
  assert.equal(input.calls.find(([name]) => name === "luna")[1].date, "2026-08-05");
});
