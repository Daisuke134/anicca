"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const {
  isVerifiedGoogleCalendarBusyInventory,
  privateGoogleCalendarBusyContext,
} = require("./google-calendar-busy-inventory.js");

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const VERIFIED = new WeakSet();
const BUFFER_MINUTES = 5;
const ADJACENT_LOCATION_MINUTES = 90;

function invalid() { throw new Error("Calendar candidate gate invalid"); }

function safeLocation(value) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!text || text.length > 2_000 || /[\x00-\x1f\x7f]/.test(text)) invalid();
  return text;
}

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

function directConflicts(event, inventory) {
  const start = Date.parse(event.starts_at);
  const end = Date.parse(event.ends_at);
  const eventDate = localDate(event.starts_at, inventory.time_zone);
  return inventory.busy_intervals.filter((busy) => {
    if (busy.kind === "all_day") return busy.start_date <= eventDate && eventDate < busy.end_date;
    return overlaps(start, end, Date.parse(busy.start_at), Date.parse(busy.end_at));
  });
}

function adjacentLocation(event, inventory, direction, home) {
  const start = Date.parse(event.starts_at);
  const end = Date.parse(event.ends_at);
  let selected = null;
  for (const busy of inventory.busy_intervals) {
    if (busy.kind !== "timed") continue;
    const privateContext = privateGoogleCalendarBusyContext(inventory, busy.event_ref);
    if (!privateContext.location) continue;
    if (direction === "inbound") {
      const gap = start - Date.parse(busy.end_at);
      if (gap < 0 || gap > ADJACENT_LOCATION_MINUTES * 60_000) continue;
      if (!selected || Date.parse(busy.end_at) > Date.parse(selected.busy.end_at)) {
        selected = { busy, location: privateContext.location };
      }
    } else {
      const gap = Date.parse(busy.start_at) - end;
      if (gap < 0 || gap > ADJACENT_LOCATION_MINUTES * 60_000) continue;
      if (!selected || Date.parse(busy.start_at) < Date.parse(selected.busy.start_at)) {
        selected = { busy, location: privateContext.location };
      }
    }
  }
  return selected ? selected.location : home;
}

async function routeDuration(routeMinutes, input) {
  if (input.from === input.to) return 0;
  let value;
  try { value = await routeMinutes(input); } catch { return null; }
  return Number.isFinite(value) && value >= 0 && value <= 24 * 60 ? value : null;
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
    || typeof input.routeMinutes !== "function"
  ) invalid();
  const day = dateInventory.days.find((candidate) => candidate.date === date);
  if (!day || day.inventory_status !== "complete") invalid();
  const home = safeLocation(input.homeLocation);
  const candidates = [];
  for (const event of day.events) {
    const direct = directConflicts(event, busyInventory);
    if (direct.length > 0) {
      candidates.push(Object.freeze({
        event_ref: event.event_ref,
        eligible: false,
        expanded_start_at: event.starts_at,
        expanded_end_at: event.ends_at,
        inbound_minutes: null,
        outbound_minutes: null,
        conflict_event_refs: Object.freeze(direct.map((busy) => busy.event_ref)),
      }));
      continue;
    }
    const venue = safeLocation(event.venue_address || event.venue_name);
    const origin = adjacentLocation(event, busyInventory, "inbound", home);
    const destination = adjacentLocation(event, busyInventory, "outbound", home);
    const inbound = await routeDuration(input.routeMinutes, {
      direction: "inbound", from: origin, to: venue,
      event_ref: event.event_ref, anchor_at: event.starts_at,
    });
    if (inbound === null) return finish({
      date,
      busy_inventory_id: busyInventory.busy_inventory_id,
      inventory_snapshot_id: dateInventory.inventory_snapshot_id,
      status: "recovery_required",
      reason: "route_unavailable",
      failed_event_ref: event.event_ref,
      candidates: Object.freeze([]),
    });
    const outbound = await routeDuration(input.routeMinutes, {
      direction: "outbound", from: venue, to: destination,
      event_ref: event.event_ref, anchor_at: event.ends_at,
    });
    if (outbound === null) return finish({
      date,
      busy_inventory_id: busyInventory.busy_inventory_id,
      inventory_snapshot_id: dateInventory.inventory_snapshot_id,
      status: "recovery_required",
      reason: "route_unavailable",
      failed_event_ref: event.event_ref,
      candidates: Object.freeze([]),
    });
    const expandedStart = Date.parse(event.starts_at) - (inbound + BUFFER_MINUTES) * 60_000;
    const expandedEnd = Date.parse(event.ends_at) + (outbound + BUFFER_MINUTES) * 60_000;
    const conflicts = busyInventory.busy_intervals.filter((busy) => (
      busy.kind === "timed"
      && overlaps(expandedStart, expandedEnd, Date.parse(busy.start_at), Date.parse(busy.end_at))
    ));
    candidates.push(Object.freeze({
      event_ref: event.event_ref,
      eligible: conflicts.length === 0,
      expanded_start_at: new Date(expandedStart).toISOString(),
      expanded_end_at: new Date(expandedEnd).toISOString(),
      inbound_minutes: inbound,
      outbound_minutes: outbound,
      conflict_event_refs: Object.freeze(conflicts.map((busy) => busy.event_ref)),
    }));
  }
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

function isVerifiedCalendarCandidateGate(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  evaluateCalendarCandidateGate,
  isVerifiedCalendarCandidateGate,
};
