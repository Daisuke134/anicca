"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedEventSourceHandoff } = require("./event-source-handoff.js");

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const VERIFIED = new WeakSet();

function invalid() { throw new Error("Calendar candidate gate invalid"); }

function localDate(instant, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function overlaps(startA, endA, startB, endB) {
  return startA < endB && endA > startB;
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

function finish(core) {
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const result = Object.freeze({ calendar_gate_id: `calendar-candidate-gate:${digest}`, ...core });
  VERIFIED.add(result);
  return result;
}

async function mapWithConcurrency(values, limit, operation) {
  if (!Array.isArray(values) || !Number.isInteger(limit) || limit < 1 || typeof operation !== "function") invalid();
  const results = new Array(values.length);
  let next = 0;
  async function worker() {
    while (next < values.length) {
      const index = next;
      next += 1;
      results[index] = await operation(values[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, values.length) }, worker));
  return results;
}

function directConflicts(event, inventory) {
  const start = Date.parse(event.starts_at);
  const end = Date.parse(event.ends_at);
  const eventDate = localDate(event.starts_at, inventory.time_zone);
  return inventory.busy_intervals.filter((busy) => {
    if (busy.kind === "all_day") return busy.start_date <= eventDate && eventDate < busy.end_date;
    return overlaps(start, end, Date.parse(busy.start_at), Date.parse(busy.end_at));
  });
}

async function evaluateEvents(events, busyInventory) {
  return mapWithConcurrency(events, 4, async (event) => {
    const direct = directConflicts(event, busyInventory);
    return Object.freeze({
      event_ref: event.event_ref,
      eligible: direct.length === 0,
      conflict_event_refs: Object.freeze(direct.map((busy) => busy.event_ref)),
    });
  });
}

async function evaluateCalendarCandidateGate(input = {}) {
  const dateInventory = input.dateInventory;
  const busyInventory = input.busyInventory;
  const date = String(input.date == null ? "" : input.date).trim();
  if (
    !isVerifiedLumaDateInventory(dateInventory)
    || !isVerifiedGoogleCalendarBusyInventory(busyInventory)
    || !DATE.test(date)
    || dateInventory.timezone !== busyInventory.time_zone
  ) invalid();
  const day = dateInventory.days.find((candidate) => candidate.date === date);
  if (!day || day.inventory_status !== "complete") invalid();
  const candidates = await evaluateEvents(day.events, busyInventory);
  return finish({
    date,
    busy_inventory_id: busyInventory.busy_inventory_id,
    inventory_snapshot_id: dateInventory.inventory_snapshot_id,
    status: "evaluated",
    reason: null,
    failed_event_ref: null,
    candidates: Object.freeze(candidates),
  });
}

async function evaluateConnpassCalendarCandidateGate(input = {}) {
  const handoff = input.handoff;
  const busyInventory = input.busyInventory;
  if (
    !isVerifiedEventSourceHandoff(handoff)
    || handoff.status !== "advisory_candidates_found"
    || !isVerifiedGoogleCalendarBusyInventory(busyInventory)
    || handoff.coverage_credit_count !== 0
  ) invalid();
  const candidates = await evaluateEvents(handoff.advisory_candidates, busyInventory);
  return finish({
    date: handoff.date, busy_inventory_id: busyInventory.busy_inventory_id,
    inventory_snapshot_id: handoff.handoff_id, status: "evaluated", reason: null,
    failed_event_ref: null, candidates: Object.freeze(candidates),
  });
}

function isVerifiedCalendarCandidateGate(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

function calendarEligibleLumaCandidates(dateInventory, gate) {
  if (
    !isVerifiedLumaDateInventory(dateInventory)
    || !isVerifiedCalendarCandidateGate(gate)
    || gate.status !== "evaluated"
    || gate.inventory_snapshot_id !== dateInventory.inventory_snapshot_id
  ) invalid();
  const day = dateInventory.days.find((candidate) => candidate.date === gate.date);
  if (!day || gate.candidates.length !== day.events.length) invalid();
  const events = new Map(day.events.map((event) => [event.event_ref, event]));
  const seen = new Set();
  const selected = [];
  for (const row of gate.candidates) {
    const event = events.get(row.event_ref);
    if (!event || seen.has(row.event_ref)) invalid();
    seen.add(row.event_ref);
    if (row.eligible) selected.push(Object.freeze({
      event_ref: event.event_ref,
      canonical_url: event.canonical_url,
    }));
  }
  if (seen.size !== events.size) invalid();
  return Object.freeze(selected);
}

function calendarEligibleConnpassCandidates(handoff, gate) {
  if (
    !isVerifiedEventSourceHandoff(handoff)
    || !isVerifiedCalendarCandidateGate(gate)
    || gate.status !== "evaluated"
    || gate.inventory_snapshot_id !== handoff.handoff_id
    || gate.candidates.length !== handoff.advisory_candidates.length
  ) invalid();
  const events = new Map(handoff.advisory_candidates.map((event) => [event.event_ref, event]));
  return Object.freeze(gate.candidates.filter((row) => row.eligible).map((row) => {
    const event = events.get(row.event_ref);
    if (!event) invalid();
    return event;
  }));
}

module.exports = {
  calendarEligibleConnpassCandidates,
  calendarEligibleLumaCandidates,
  evaluateCalendarCandidateGate,
  evaluateConnpassCalendarCandidateGate,
  isVerifiedCalendarCandidateGate,
  mapWithConcurrency,
};
