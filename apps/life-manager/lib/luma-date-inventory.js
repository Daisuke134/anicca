"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedLumaInventory } = require("./luma-discovery.js");
const { isVerifiedLumaEventDetail } = require("./luma-event-detail.js");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");

const VERIFIED = new WeakSet();

function invalid() { throw new Error("Luma date inventory invalid"); }

function exactInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const ms = Date.parse(text);
  if (!Number.isFinite(ms) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
  return new Date(ms).toISOString();
}

function localDateKey(instant, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
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

function projectedEvent(detail) {
  return Object.freeze({
    event_ref: detail.event_ref,
    canonical_url: detail.canonical_url,
    title: detail.title,
    starts_at: detail.starts_at,
    ends_at: detail.ends_at,
    venue_name: detail.venue_name,
    venue_address: detail.venue_address,
    description: detail.description,
    organizer_names: detail.organizer_names,
    participant_descriptors: detail.participant_descriptors,
    participant_visibility: detail.participant_visibility,
    rsvp_status: detail.rsvp_status,
  });
}

function buildLumaDateInventory(input = {}) {
  const coverage = input.coverage;
  const inventory = input.inventory;
  const details = input.details;
  if (
    !isVerifiedRollingEventCoverage(coverage)
    || !isVerifiedLumaInventory(inventory)
    || inventory.complete !== true
    || !Array.isArray(details)
  ) invalid();
  const calculatedAt = exactInstant(input.now);
  const candidateUrls = inventory.candidates.map((candidate) => candidate.canonical_url);
  if (candidateUrls.length !== new Set(candidateUrls).size || details.length !== candidateUrls.length) invalid();
  const expected = new Set(candidateUrls);
  const actual = new Set();
  for (const detail of details) {
    if (!isVerifiedLumaEventDetail(detail) || actual.has(detail.canonical_url)) invalid();
    actual.add(detail.canonical_url);
  }
  if (actual.size !== expected.size || [...expected].some((url) => !actual.has(url))) invalid();

  const byDate = new Map(coverage.days.map((day) => [day.date, []]));
  let included = 0;
  for (const detail of details) {
    if (detail.event_status !== "scheduled" || detail.attendance_mode !== "in_person") continue;
    const date = localDateKey(detail.starts_at, coverage.timezone);
    const events = byDate.get(date);
    if (!events) continue;
    events.push(projectedEvent(detail));
    included += 1;
  }
  const days = Object.freeze(coverage.days.map((coverageDay) => {
    const events = byDate.get(coverageDay.date);
    events.sort((left, right) => (
      left.starts_at.localeCompare(right.starts_at) || left.event_ref.localeCompare(right.event_ref)
    ));
    return Object.freeze({
      date: coverageDay.date,
      inventory_status: "complete",
      events: Object.freeze(events),
    });
  }));
  const datesWithCandidates = days.filter((day) => day.events.length > 0).length;
  const counts = Object.freeze({
    discovered: candidateUrls.length,
    inspected: details.length,
    scheduled_in_person_in_window: included,
    excluded: details.length - included,
    dates_with_candidates: datesWithCandidates,
    dates_without_candidates: days.length - datesWithCandidates,
  });
  const core = {
    provider: "luma",
    complete: true,
    coverage_snapshot_id: coverage.coverage_snapshot_id,
    timezone: coverage.timezone,
    calculated_at: calculatedAt,
    window_start_date: coverage.window_start_date,
    window_end_date: coverage.window_end_date,
    source_inventory_rounds: inventory.rounds,
    counts,
    days,
  };
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const snapshot = Object.freeze({ inventory_snapshot_id: `luma-date-inventory:${digest}`, ...core });
  VERIFIED.add(snapshot);
  return snapshot;
}

async function inspectLumaDateInventory(options = {}) {
  if (
    typeof options.discoverTokyo !== "function"
    || typeof options.inspectEvent !== "function"
  ) invalid();
  const inventory = await options.discoverTokyo();
  const details = [];
  for (const candidate of inventory && Array.isArray(inventory.candidates) ? inventory.candidates : []) {
    details.push(await options.inspectEvent(candidate.canonical_url));
  }
  return buildLumaDateInventory({
    coverage: options.coverage,
    inventory,
    details,
    now: options.now,
  });
}

function isVerifiedLumaDateInventory(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  buildLumaDateInventory,
  inspectLumaDateInventory,
  isVerifiedLumaDateInventory,
};
