"use strict";

const { createHash } = require("node:crypto");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const { isVerifiedEventSourceHandoff } = require("./event-source-handoff.js");

const VERIFIED = new WeakSet();

function invalid() { throw new Error("Event provider date inventory invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function instant(value) {
  const text = String(value || "");
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== text) invalid();
  return text;
}

function eventProjection(event) {
  if (
    !event || event.provider !== "connpass"
    || !/^connpass-event:\/\/event\/[1-9][0-9]*$/.test(String(event.event_ref || ""))
    || event.registration_allowed !== false || event.coverage_credit !== false
  ) invalid();
  return Object.freeze({
    provider: "connpass",
    event_ref: event.event_ref,
    canonical_url: event.canonical_url,
    title: event.title,
    starts_at: instant(new Date(Date.parse(event.starts_at)).toISOString()),
    ends_at: instant(new Date(Date.parse(event.ends_at)).toISOString()),
    venue_name: event.venue_name,
    venue_address: event.address,
    description: event.description,
  });
}

function buildEventProviderDateInventory(input = {}) {
  const coverage = input.coverage;
  const handoff = input.handoff;
  const eligible = input.eligibleCandidates;
  if (
    !isVerifiedRollingEventCoverage(coverage)
    || !isVerifiedEventSourceHandoff(handoff)
    || handoff.status !== "advisory_candidates_found"
    || handoff.coverage_credit_count !== 0
    || !coverage.days.some((day) => day.date === handoff.date && day.status === "open")
    || !Array.isArray(eligible)
    || eligible.some((event) => !handoff.advisory_candidates.includes(event))
    || new Set(eligible).size !== eligible.length
  ) invalid();
  const calculatedAt = instant(input.now);
  const projected = Object.freeze(eligible.map(eventProjection).sort((left, right) => (
    left.starts_at.localeCompare(right.starts_at) || left.event_ref.localeCompare(right.event_ref)
  )));
  const days = Object.freeze(coverage.days.map((day) => Object.freeze({
    date: day.date,
    inventory_status: "complete",
    events: day.date === handoff.date ? projected : Object.freeze([]),
  })));
  const core = {
    provider: "connpass",
    complete: true,
    coverage_snapshot_id: coverage.coverage_snapshot_id,
    timezone: coverage.timezone,
    calculated_at: calculatedAt,
    window_start_date: coverage.window_start_date,
    window_end_date: coverage.window_end_date,
    source_handoff_id: handoff.handoff_id,
    counts: Object.freeze({ eligible: projected.length }),
    days,
  };
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const result = Object.freeze({
    inventory_snapshot_id: `event-provider-date-inventory:${digest}`,
    ...core,
  });
  VERIFIED.add(result);
  return result;
}

function isVerifiedEventProviderDateInventory(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  buildEventProviderDateInventory,
  isVerifiedEventProviderDateInventory,
};
