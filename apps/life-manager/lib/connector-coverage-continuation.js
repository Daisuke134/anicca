"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");

const OUTCOMES = new Set([
  "booked",
  "operation_failed",
  "reconciliation_required",
  "recovery_required",
  "search_exhausted",
  "source_failed",
]);
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const VERIFIED = new WeakSet();

function invalid() { throw new Error("Connector coverage continuation invalid"); }

function exactInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const time = Date.parse(text);
  if (!Number.isFinite(time) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
  return new Date(time).toISOString();
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function planConnectorCoverageContinuation(input = {}) {
  const coverage = input.coverage;
  if (!isVerifiedRollingEventCoverage(coverage) || !Array.isArray(input.observedOutcomes)) invalid();
  const now = exactInstant(input.now);
  const allowedDates = new Set(coverage.days.map((day) => day.date));
  const outcomes = input.observedOutcomes.map((value) => {
    if (
      !value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join(",") !== "date,observed_status"
    ) invalid();
    const date = String(value.date == null ? "" : value.date).trim();
    const observedStatus = String(value.observed_status == null ? "" : value.observed_status).trim();
    if (!DATE.test(date) || !allowedDates.has(date) || !OUTCOMES.has(observedStatus)) invalid();
    return Object.freeze({ date, observed_status: observedStatus });
  });

  const complete = coverage.counts.open === 0;
  let nextAction = null;
  if (!complete) {
    if (outcomes.some((outcome) => outcome.observed_status === "reconciliation_required")) {
      nextAction = "reconcile_effect";
    } else if (outcomes.some((outcome) => outcome.observed_status === "recovery_required")) {
      nextAction = "recover_source";
    } else {
      nextAction = "refresh_inventory";
    }
  }
  const core = {
    coverage_snapshot_id: coverage.coverage_snapshot_id,
    status: complete ? "complete" : "continue",
    open_date_count: coverage.counts.open,
    next_action: nextAction,
    next_run_at: complete ? null : new Date(Date.parse(now) + 300_000).toISOString(),
  };
  const digest = createHash("sha256").update(stableJson({ ...core, outcomes }), "utf8").digest("hex");
  const result = Object.freeze({
    continuation_id: `connector-coverage-continuation:${digest}`,
    ...core,
  });
  VERIFIED.add(result);
  return result;
}

function isVerifiedConnectorCoverageContinuation(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  isVerifiedConnectorCoverageContinuation,
  planConnectorCoverageContinuation,
};
