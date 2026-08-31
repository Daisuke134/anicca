"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedConnectorProfile } = require("./connector-profile.js");

const VERIFIED = new WeakSet();
const UNAVAILABLE_EVIDENCE = new WeakMap();
const ACTIVE = new Set(["queued", "running", "reconciling", "completed"]);
const ALL_STATUSES = new Set([...ACTIVE, "dead_letter"]);
const SKIP_REASON = /^[a-z][a-z0-9_]{0,99}$/;

function invalid() { throw new Error("Connector open-date planner invalid"); }

async function stage(code, operation) {
  try {
    return await operation();
  } catch (cause) {
    const error = new Error("Connector open-date planning unavailable");
    const goalMatch = code === "CONNECTOR_COVERAGE_APPLICATION_GOAL_EVALUATION_FAILED"
      ? /^EVENT_GOAL_SERENDIPITY_(CONFIG|TRANSPORT|HTTP|BODY|JSON|VALIDATION(?:_(?:SHAPE|COUNT|EVENT_REF|TEXT|GROUNDED))?)_FAILED$/.exec(
        String(cause && cause.code || ""),
      )
      : null;
    error.code = goalMatch
      ? `CONNECTOR_COVERAGE_APPLICATION_GOAL_${goalMatch[1]}_FAILED`
      : code;
    throw error;
  }
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function result(core, unavailableEvidence = null) {
  const value = Object.freeze({
    open_date_plan_id: `connector-open-date-plan:${createHash("sha256").update(stableJson(core), "utf8").digest("hex")}`,
    ...core,
  });
  VERIFIED.add(value);
  if (unavailableEvidence != null) UNAVAILABLE_EVIDENCE.set(value, unavailableEvidence);
  return value;
}

function aggregateSequence(day, sequence) {
  if (!Array.isArray(sequence.ordered_candidates) || !Array.isArray(sequence.skipped)) invalid();
  const expected = new Set(day.events.map((event) => event.event_ref));
  const seen = new Set();
  const counts = new Map();
  for (const candidate of sequence.ordered_candidates) {
    const ref = String(candidate && candidate.event_ref || "");
    if (!expected.has(ref) || seen.has(ref)) invalid();
    seen.add(ref);
  }
  for (const skipped of sequence.skipped) {
    const ref = String(skipped && skipped.event_ref || "");
    const reason = String(skipped && skipped.reason || "");
    if (!expected.has(ref) || seen.has(ref) || !SKIP_REASON.test(reason)) invalid();
    seen.add(ref);
    counts.set(reason, (counts.get(reason) || 0) + 1);
  }
  if (seen.size !== expected.size) invalid();
  return Object.freeze({
    candidate_count: day.events.length,
    runnable_candidate_count: sequence.ordered_candidates.length,
    skip_reason_counts: Object.freeze([...counts.entries()].sort(([left], [right]) => left.localeCompare(right))
      .map(([reason, count]) => Object.freeze({ reason, count }))),
  });
}

function dependenciesContract(dependencies) {
  const names = [
    "rankDatePreferences", "evaluateDateGoals", "gateDateCalendar",
    "createSpendPolicy", "buildSpendSequence", "buildApplicationJob",
    "readApplicationJob", "enqueueApplication", "proveCalendarUnavailable",
  ];
  if (names.some((name) => typeof dependencies[name] !== "function")) invalid();
}

function createConnectorOpenDateApplicationPlanner(dependencies = {}) {
  dependenciesContract(dependencies);
  return async function planOpenDate(input = {}) {
    const { coverage, dateInventory, busyInventory, profile } = input;
    if (
      !isVerifiedRollingEventCoverage(coverage)
      || !isVerifiedLumaDateInventory(dateInventory)
      || !isVerifiedGoogleCalendarBusyInventory(busyInventory)
      || !isVerifiedConnectorProfile(profile)
      || coverage.tenant_id !== profile.tenant_id
      || coverage.timezone !== profile.timezone
      || dateInventory.timezone !== coverage.timezone
      || dateInventory.window_start_date !== coverage.window_start_date
      || dateInventory.window_end_date !== coverage.window_end_date
    ) invalid();
    const openDays = coverage.days.filter((day) => day.status === "open");
    if (openDays.length === 0) return result({
      coverage_snapshot_id: coverage.coverage_snapshot_id,
      inventory_snapshot_id: dateInventory.inventory_snapshot_id,
      date: null, status: "complete", event_ref: null, job_ref: null,
      candidate_count: 0, runnable_candidate_count: 0, skip_reason_counts: Object.freeze([]),
    });
    let lastExhausted;
    for (const open of openDays) {
    const day = dateInventory.days.find((candidate) => candidate.date === open.date);
    if (!day || day.inventory_status !== "complete") invalid();
    const ranking = await stage("CONNECTOR_COVERAGE_APPLICATION_RANKING_FAILED", () => (
      dependencies.rankDatePreferences(
        dateInventory, open.date, profile.preferences, { apiKey: input.apiKey },
      )
    ));
    const goals = await stage("CONNECTOR_COVERAGE_APPLICATION_GOAL_EVALUATION_FAILED", () => (
      dependencies.evaluateDateGoals(
        dateInventory, ranking, profile.goals, { apiKey: input.apiKey },
      )
    ));
    const gate = await stage("CONNECTOR_COVERAGE_APPLICATION_CALENDAR_GATE_FAILED", () => (
      dependencies.gateDateCalendar(dateInventory, busyInventory, open.date)
    ));
    const sequence = await stage("CONNECTOR_COVERAGE_APPLICATION_SPEND_PLAN_FAILED", async () => {
      const policy = await dependencies.createSpendPolicy({
        tenantId: profile.tenant_id,
        limits: profile.spend_policy.limits,
      });
      return dependencies.buildSpendSequence(policy, dateInventory, gate, goals);
    });
    const eventByRef = new Map(day.events.map((event) => [event.event_ref, event]));
    if (!sequence || !Array.isArray(sequence.ordered_candidates) || !Array.isArray(sequence.skipped)) invalid();
    const runnable = [];
    const unavailable = [];
    for (const candidate of sequence.ordered_candidates) {
      const event = eventByRef.get(candidate && candidate.event_ref);
      if (!event || candidate.canonical_url !== event.canonical_url) invalid();
      if (event.rsvp_status === "available") runnable.push(candidate);
      else unavailable.push({
        event_ref: event.event_ref,
        reason: `rsvp_${String(event.rsvp_status || "unknown")}`,
      });
    }
    const effectiveSequence = {
      ordered_candidates: runnable,
      skipped: [...sequence.skipped, ...unavailable],
    };
    const aggregate = aggregateSequence(day, effectiveSequence);
    const candidates = runnable.map((candidate) => eventByRef.get(candidate.event_ref));
    if (new Set(candidates.map((event) => event.event_ref)).size !== candidates.length) invalid();
    const base = {
      coverage_snapshot_id: coverage.coverage_snapshot_id,
      inventory_snapshot_id: dateInventory.inventory_snapshot_id,
      date: open.date,
      ...aggregate,
    };
    if (
      aggregate.candidate_count > 0
      && aggregate.runnable_candidate_count === 0
      && aggregate.skip_reason_counts.length === 1
      && aggregate.skip_reason_counts[0].reason === "calendar_conflict"
    ) {
      const unavailableEvidence = await stage("CONNECTOR_COVERAGE_APPLICATION_CALENDAR_UNAVAILABLE_PROOF_FAILED", () => (
        dependencies.proveCalendarUnavailable({
          dateInventory, busyInventory, calendarGate: gate, date: open.date,
        })
      ));
      return result({ ...base, status: "unavailable", event_ref: null, job_ref: null }, unavailableEvidence);
    }
    if (candidates.length === 0) {
      lastExhausted = {
      ...base, status: day.events.length === 0 ? "no_candidates" : "exhausted",
      event_ref: null, job_ref: null,
      };
      continue;
    }
    for (const event of candidates) {
      const application = {
        tenantId: profile.tenant_id,
        eventUrl: event.canonical_url,
        eventStartIso: event.starts_at,
        identityRef: profile.identity_ref,
        browserProfileRef: profile.browser_profile_ref,
        calendarRef: profile.calendar_ref,
      };
      const job = await stage("CONNECTOR_COVERAGE_APPLICATION_JOB_BUILD_FAILED", () => (
        dependencies.buildApplicationJob(application)
      ));
      const stored = await stage("CONNECTOR_COVERAGE_APPLICATION_JOB_READ_FAILED", () => (
        dependencies.readApplicationJob(job)
      ));
      if (stored != null) {
        if (!stored || !ALL_STATUSES.has(stored.status)) invalid();
        if (ACTIVE.has(stored.status)) return result({
          ...base, status: "waiting", event_ref: event.event_ref,
          job_ref: `runtime-job://${profile.tenant_id}/${job.job_id.replace(/^outbound-event:/, "")}`,
        });
        continue;
      }
      const enqueued = await stage("CONNECTOR_COVERAGE_APPLICATION_JOB_ENQUEUE_FAILED", () => (
        dependencies.enqueueApplication(application)
      ));
      if (
        !enqueued || enqueued.created !== true || !enqueued.job
        || enqueued.job.job_id !== job.job_id || enqueued.job.status !== "queued"
      ) invalid();
      return result({
        ...base, status: "enqueued", event_ref: event.event_ref,
        job_ref: `runtime-job://${profile.tenant_id}/${job.job_id.replace(/^outbound-event:/, "")}`,
      });
    }
    lastExhausted = { ...base, status: "exhausted", event_ref: null, job_ref: null };
    }
    return result(lastExhausted);
  };
}

function isVerifiedConnectorOpenDatePlan(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

function unavailableEvidenceForConnectorOpenDatePlan(value) {
  if (!isVerifiedConnectorOpenDatePlan(value) || value.status !== "unavailable") invalid();
  const evidence = UNAVAILABLE_EVIDENCE.get(value);
  if (!evidence) invalid();
  return evidence;
}

function rebindUnavailableConnectorOpenDatePlan(value, coverage) {
  if (
    !isVerifiedConnectorOpenDatePlan(value)
    || value.status !== "unavailable"
    || !isVerifiedRollingEventCoverage(coverage)
    || !coverage.days.some((day) => day.date === value.date && day.status === "unavailable")
  ) invalid();
  const evidence = unavailableEvidenceForConnectorOpenDatePlan(value);
  const { open_date_plan_id: _ignored, ...core } = value;
  return result({ ...core, coverage_snapshot_id: coverage.coverage_snapshot_id }, evidence);
}

module.exports = {
  createConnectorOpenDateApplicationPlanner,
  isVerifiedConnectorOpenDatePlan,
  rebindUnavailableConnectorOpenDatePlan,
  unavailableEvidenceForConnectorOpenDatePlan,
};
