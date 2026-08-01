"use strict";

const { createHash } = require("node:crypto");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedConnectorCalendarSync } = require("./connector-calendar-sync.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const REGISTRATIONS = new WeakSet();
const UNAVAILABLE = new WeakSet();

function invalid() { throw new Error("Connector coverage assembler invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function digest(value) {
  return createHash("sha256").update(stableJson(value), "utf8").digest("hex");
}

function localDate(instant, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function buildVerifiedRegistrationCoverageEvidence(input = {}) {
  const dateInventory = input.dateInventory;
  const calendarSync = input.calendarSync;
  if (
    !isVerifiedLumaDateInventory(dateInventory)
    || !isVerifiedConnectorCalendarSync(calendarSync)
    || !["created", "existing"].includes(calendarSync.status)
  ) invalid();
  const event = dateInventory.days.flatMap((day) => day.events)
    .find((candidate) => candidate.event_ref === calendarSync.event_ref);
  if (!event || event.canonical_url !== calendarSync.canonical_event_url) invalid();
  const core = {
    date: localDate(event.starts_at, dateInventory.timezone),
    status: calendarSync.status === "created" ? "covered_new" : "covered_existing",
    event_ref: event.event_ref,
    inventory_snapshot_id: dateInventory.inventory_snapshot_id,
    calendar_sync_id: calendarSync.calendar_sync_id,
    evidence_refs: Object.freeze([
      calendarSync.registration_receipt_ref,
      calendarSync.calendar_event_ref,
    ]),
  };
  const evidence = Object.freeze({
    registration_coverage_evidence_id: `registration-coverage-evidence:${digest(core)}`,
    ...core,
  });
  REGISTRATIONS.add(evidence);
  return evidence;
}

function proveAllDayCalendarUnavailable(input = {}) {
  const busyInventory = input.busyInventory;
  const date = String(input.date == null ? "" : input.date).trim();
  if (!isVerifiedGoogleCalendarBusyInventory(busyInventory) || !DATE.test(date)) invalid();
  const blockers = busyInventory.busy_intervals.filter((interval) => (
    interval.kind === "all_day" && interval.start_date <= date && date < interval.end_date
  ));
  if (blockers.length === 0) throw new Error("Connector calendar day not unavailable");
  const core = {
    date,
    busy_inventory_id: busyInventory.busy_inventory_id,
    evidence_refs: Object.freeze(blockers.map((interval) => interval.event_ref).sort()),
  };
  const evidence = Object.freeze({
    calendar_unavailable_evidence_id: `calendar-unavailable-evidence:${digest(core)}`,
    ...core,
  });
  UNAVAILABLE.add(evidence);
  return evidence;
}

function rebuildRollingEventCoverage(input = {}) {
  if (!Array.isArray(input.registrations) || !Array.isArray(input.unavailableDays)) invalid();
  const empty = buildRollingEventCoverage({
    tenantId: input.tenantId,
    timeZone: input.timeZone,
    now: input.now,
    resolvedDays: [],
  });
  const allowedDates = new Set(empty.days.map((day) => day.date));
  const byDate = new Map();
  for (const registration of input.registrations) {
    if (!REGISTRATIONS.has(registration) || !allowedDates.has(registration.date)) invalid();
    const existing = byDate.get(registration.date);
    if (!existing) {
      byDate.set(registration.date, {
        status: registration.status,
        evidence_refs: [...registration.evidence_refs],
      });
      continue;
    }
    if (registration.status === "covered_new") existing.status = "covered_new";
    existing.evidence_refs.push(...registration.evidence_refs);
  }
  for (const unavailable of input.unavailableDays) {
    if (!UNAVAILABLE.has(unavailable) || !allowedDates.has(unavailable.date) || byDate.has(unavailable.date)) invalid();
    byDate.set(unavailable.date, {
      status: "unavailable",
      evidence_refs: [...unavailable.evidence_refs],
    });
  }
  const resolvedDays = [...byDate.entries()].map(([date, value]) => {
    const evidenceRefs = [...new Set(value.evidence_refs)];
    if (evidenceRefs.length !== value.evidence_refs.length) invalid();
    return { date, status: value.status, evidence_refs: evidenceRefs };
  });
  return buildRollingEventCoverage({
    tenantId: input.tenantId,
    timeZone: input.timeZone,
    now: input.now,
    resolvedDays,
  });
}

module.exports = {
  buildVerifiedRegistrationCoverageEvidence,
  proveAllDayCalendarUnavailable,
  rebuildRollingEventCoverage,
};
