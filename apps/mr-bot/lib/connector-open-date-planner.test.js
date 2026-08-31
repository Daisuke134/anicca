"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { readConnectorProfile } = require("./connector-profile.js");
const { buildEventApplicationJob } = require("./outbound-event-job.js");
const {
  createConnectorOpenDateApplicationPlanner,
  isVerifiedConnectorOpenDatePlan,
  rebindUnavailableConnectorOpenDatePlan,
  unavailableEvidenceForConnectorOpenDatePlan,
} = require("./connector-open-date-planner.js");

const NOW = "2026-08-01T16:00:00.000Z";
const PROFILE = path.join(__dirname, "../config/connector/dais-local.json");

async function sources(options = {}) {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo", now: NOW, resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? [
      { href: "https://luma.com/first-a", title: "First A", cardText: "First A", timelineText: "Aug 2" },
      { href: "https://luma.com/first-b", title: "First B", cardText: "First B", timelineText: "Aug 2" },
      { href: "https://luma.com/later", title: "Later", cardText: "Later", timelineText: "Aug 3" },
    ] : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
  const detail = (slug, name, start, end) => normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event", name, description: `${name} public gathering`,
      startDate: start, endDate: end,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { name: "Tokyo Hall", address: "Tokyo" },
      offers: { price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock" },
    }],
    controls: options.controlsBySlug && options.controlsBySlug[slug] || ["Register"],
  });
  const dateInventory = buildLumaDateInventory({
    coverage,
    inventory,
    details: [
      detail("first-a", "First A", "2026-08-02T18:00:00+09:00", "2026-08-02T19:00:00+09:00"),
      detail("first-b", "First B", "2026-08-02T20:00:00+09:00", "2026-08-02T21:00:00+09:00"),
      detail("later", "Later", "2026-08-03T18:00:00+09:00", "2026-08-03T19:00:00+09:00"),
    ],
    now: NOW,
  });
  const busyInventory = await inspectGoogleCalendarBusyInventory({
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() { return []; },
    },
    timeMin: "2026-08-01T15:00:00.000Z", timeMax: "2026-08-22T15:00:00.000Z",
    timeZone: "Asia/Tokyo", now: NOW,
  });
  return {
    coverage, dateInventory, busyInventory,
    profile: readConnectorProfile({ path: PROFILE, tenantId: "dais-local" }),
  };
}

function planner(statuses = new Map(), overrides = {}) {
  const calls = [];
  const instance = createConnectorOpenDateApplicationPlanner({
    async rankDatePreferences(_inventory, date) { calls.push(["rank", date]); return { date }; },
    async evaluateDateGoals(_inventory, ranking) { calls.push(["goals", ranking.date]); return { date: ranking.date }; },
    async gateDateCalendar(_inventory, _busy, date) { calls.push(["gate", date]); return { date }; },
    createSpendPolicy() { return { policy: "free-only" }; },
    buildSpendSequence(_policy, inventory, _gate, goal) {
      const day = inventory.days.find((row) => row.date === goal.date);
      return {
        ordered_candidates: day.events.map(({ event_ref, canonical_url }) => ({ event_ref, canonical_url })),
        skipped: [],
      };
    },
    buildApplicationJob: buildEventApplicationJob,
    async readApplicationJob(job) {
      const eventRef = job.input_refs.event_ref.split("?")[0];
      calls.push(["read", eventRef]);
      return statuses.get(eventRef) || null;
    },
    async enqueueApplication(input) {
      const job = buildEventApplicationJob(input);
      calls.push(["enqueue", job.input_refs.event_ref.split("?")[0]]);
      return { created: true, job: { ...job, status: "queued" } };
    },
    proveCalendarUnavailable() {
      return Object.freeze({
        date: "2026-08-02",
        evidence_refs: Object.freeze([`calendar-evidence://google/event/${"e".repeat(64)}`]),
      });
    },
    ...overrides,
  });
  return { instance, calls };
}

test("earliest open date enqueues only its first absent candidate", async () => {
  const input = await sources();
  const { instance, calls } = planner();
  const result = await instance(input);
  assert.equal(result.date, "2026-08-02");
  assert.equal(result.status, "enqueued");
  assert.match(result.event_ref, /first-a/);
  assert.equal(calls.filter(([kind]) => kind === "enqueue").length, 1);
  assert.equal(calls.some(([, value]) => value === "2026-08-03"), false);
  assert.equal(isVerifiedConnectorOpenDatePlan(result), true);
  assert.equal(isVerifiedConnectorOpenDatePlan(structuredClone(result)), false);
});

test("dependency failures expose only their bounded application-planning stage", async () => {
  const stages = [
    ["rankDatePreferences", "CONNECTOR_COVERAGE_APPLICATION_RANKING_FAILED"],
    ["evaluateDateGoals", "CONNECTOR_COVERAGE_APPLICATION_GOAL_EVALUATION_FAILED"],
    ["gateDateCalendar", "CONNECTOR_COVERAGE_APPLICATION_CALENDAR_GATE_FAILED"],
    ["createSpendPolicy", "CONNECTOR_COVERAGE_APPLICATION_SPEND_PLAN_FAILED"],
    ["readApplicationJob", "CONNECTOR_COVERAGE_APPLICATION_JOB_READ_FAILED"],
    ["enqueueApplication", "CONNECTOR_COVERAGE_APPLICATION_JOB_ENQUEUE_FAILED"],
  ];
  for (const [name, code] of stages) {
    const input = await sources();
    const { instance } = planner(new Map(), { [name]: async () => { throw new Error("private provider failure"); } });
    await assert.rejects(instance(input), (error) => (
      error.code === code && error.message === "Connector open-date planning unavailable"
    ));
  }
});

test("goal evaluation preserves only an allowlisted bounded provider substage", async () => {
  const input = await sources();
  const provider = new Error("private response body");
  provider.code = "EVENT_GOAL_SERENDIPITY_VALIDATION_TEXT_FAILED";
  const { instance } = planner(new Map(), {
    async evaluateDateGoals() { throw provider; },
  });
  await assert.rejects(instance(input), (error) => (
    error.code === "CONNECTOR_COVERAGE_APPLICATION_GOAL_VALIDATION_TEXT_FAILED"
    && error.message === "Connector open-date planning unavailable"
    && !JSON.stringify(error).includes("private response body")
  ));
});

test("active or completed first candidate waits and never enqueues the next candidate", async () => {
  for (const status of ["queued", "running", "reconciling", "completed"]) {
    const input = await sources();
    const first = input.dateInventory.days[0].events[0].event_ref;
    const { instance, calls } = planner(new Map([[first, { status }]]));
    const result = await instance(input);
    assert.equal(result.status, "waiting");
    assert.equal(result.event_ref, first);
    assert.equal(calls.some(([kind]) => kind === "enqueue"), false);
  }
});

test("dead-letter candidates advance across candidates and then across open dates", async () => {
  const input = await sources();
  const [first, second] = input.dateInventory.days[0].events.map((event) => event.event_ref);
  const next = planner(new Map([[first, { status: "dead_letter" }]]));
  const enqueued = await next.instance(input);
  assert.equal(enqueued.status, "enqueued");
  assert.equal(enqueued.event_ref, second);
  assert.deepEqual(next.calls.filter(([kind]) => kind === "enqueue"), [["enqueue", second]]);

  const terminal = planner(new Map([
    [first, { status: "dead_letter" }],
    [second, { status: "dead_letter" }],
  ]));
  const advanced = await terminal.instance(input);
  assert.equal(advanced.status, "enqueued");
  assert.match(advanced.event_ref, /later/);
  assert.equal(advanced.date, "2026-08-03");
  assert.deepEqual(terminal.calls.filter(([kind]) => kind === "enqueue"), [
    ["enqueue", "luma-event://event/later"],
  ]);
});

test("closed and unknown RSVP pages are skipped before an application job is built", async () => {
  const input = await sources({
    controlsBySlug: {
      "first-a": ["参加登録受付終了"],
      "first-b": ["ホストに連絡"],
      later: ["Register"],
    },
  });
  const { instance, calls } = planner();
  const result = await instance(input);
  assert.equal(result.status, "enqueued");
  assert.equal(result.event_ref, "luma-event://event/later");
  assert.deepEqual(calls.filter(([kind]) => kind === "enqueue"), [
    ["enqueue", "luma-event://event/later"],
  ]);
});

test("all-calendar-conflict plan resolves the day with bounded aggregate evidence", async () => {
  const input = await sources();
  const { instance } = planner(new Map(), {
    buildSpendSequence() {
      return {
        ordered_candidates: [],
        skipped: [
          { event_ref: "luma-event://event/first-a", reason: "calendar_conflict" },
          { event_ref: "luma-event://event/first-b", reason: "calendar_conflict" },
        ],
      };
    },
  });
  const result = await instance(input);
  assert.equal(result.status, "unavailable");
  assert.equal(result.candidate_count, 2);
  assert.equal(result.runnable_candidate_count, 0);
  assert.deepEqual(result.skip_reason_counts, [{ reason: "calendar_conflict", count: 2 }]);
  assert.doesNotMatch(JSON.stringify(result), /first-a|first-b|https:\/\//);
  assert.equal(unavailableEvidenceForConnectorOpenDatePlan(result).date, "2026-08-02");

  const resolvedCoverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo", now: NOW,
    resolvedDays: [{
      date: "2026-08-02", status: "unavailable",
      evidence_refs: [`calendar-evidence://google/event/${"e".repeat(64)}`],
    }],
  });
  const rebound = rebindUnavailableConnectorOpenDatePlan(result, resolvedCoverage);
  assert.equal(rebound.coverage_snapshot_id, resolvedCoverage.coverage_snapshot_id);
  assert.equal(rebound.status, "unavailable");
  assert.equal(isVerifiedConnectorOpenDatePlan(rebound), true);
});

test("calendar unavailable proof failure has its own bounded stage", async () => {
  const input = await sources();
  const { instance } = planner(new Map(), {
    buildSpendSequence() {
      return {
        ordered_candidates: [],
        skipped: input.dateInventory.days[0].events.map((event) => ({
          event_ref: event.event_ref, reason: "calendar_conflict",
        })),
      };
    },
    proveCalendarUnavailable() { throw new Error("private calendar detail"); },
  });
  await assert.rejects(instance(input), (error) => (
    error.code === "CONNECTOR_COVERAGE_APPLICATION_CALENDAR_UNAVAILABLE_PROOF_FAILED"
    && !JSON.stringify(error).includes("private calendar detail")
  ));
});
