"use strict";

const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");

const BASE_EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;

function invalid() { throw new Error("Connector coverage refresh invalid"); }
function unavailable() { throw new Error("Connector coverage refresh unavailable"); }

function nextDate(dateKey) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}

function midnight(dateKey, timeZone) {
  const [year, month, day] = String(dateKey).split("-").map(Number);
  return zonedSlotInstant({ year, month, day }, "00:00", timeZone);
}

function baseEventRef(value) {
  const ref = String(value == null ? "" : value).split("?")[0];
  if (!BASE_EVENT_REF.test(ref)) invalid();
  return ref;
}

function eventDate(inventory, eventRef) {
  const day = inventory.days.find((candidate) => (
    candidate.events.some((event) => event.event_ref === eventRef)
  ));
  if (!day) unavailable();
  return day.date;
}

function dependenciesContract(dependencies) {
  const requiredFunctions = [
    "readDateInventory",
    "readBusyCalendar",
    "gateDateCalendar",
    "syncRegistrationCalendar",
    "buildRegistrationCoverageEvidence",
    "proveUnavailableDay",
    "rebuildCoverage",
  ];
  if (
    !dependencies.receiptReader
    || typeof dependencies.receiptReader.listForCoverage !== "function"
    || !dependencies.calendar
    || typeof dependencies.calendar.findConnectorEvents !== "function"
    || typeof dependencies.calendar.createConnectorEvent !== "function"
    || requiredFunctions.some((name) => typeof dependencies[name] !== "function")
    || typeof dependencies.routeMinutes !== "function"
    || typeof dependencies.now !== "function"
    || !String(dependencies.calendarId || "").trim()
    || !String(dependencies.homeLocation || "").trim()
  ) invalid();
}

function createConnectorCoverageRefreshService(dependencies = {}) {
  dependenciesContract(dependencies);
  return async function refreshCoverage(input = {}) {
    const current = input.coverage;
    const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
    if (
      !isVerifiedRollingEventCoverage(current)
      || !tenantId || current.tenant_id !== tenantId
    ) invalid();
    const now = new Date(Date.parse(String(dependencies.now()))).toISOString();
    if (!Number.isFinite(Date.parse(now))) invalid();
    let working;
    let dateInventory;
    let busyInventory;
    let completed;
    try {
      working = dependencies.rebuildCoverage({
        tenantId,
        timeZone: current.timezone,
        now,
        registrations: [],
        unavailableDays: [],
      });
      dateInventory = await dependencies.readDateInventory({ coverage: working, now });
      busyInventory = await dependencies.readBusyCalendar({
        calendar: dependencies.calendar,
        timeMin: midnight(working.window_start_date, working.timezone),
        timeMax: midnight(nextDate(working.window_end_date), working.timezone),
        timeZone: working.timezone,
        now,
      });
      completed = await dependencies.receiptReader.listForCoverage({ tenantId, coverage: working });
    } catch { unavailable(); }
    if (
      !isVerifiedRollingEventCoverage(working)
      || !isVerifiedLumaDateInventory(dateInventory)
      || dateInventory.coverage_snapshot_id !== working.coverage_snapshot_id
      || !isVerifiedGoogleCalendarBusyInventory(busyInventory)
      || !Array.isArray(completed)
    ) unavailable();

    const registrations = [];
    const observedOutcomes = [];
    try {
      for (const completedRegistration of completed) {
        const eventRef = baseEventRef(completedRegistration.event_ref);
        const date = eventDate(dateInventory, eventRef);
        const calendarGate = await dependencies.gateDateCalendar({
          dateInventory,
          busyInventory,
          date,
          homeLocation: dependencies.homeLocation,
          routeMinutes: dependencies.routeMinutes,
        });
        const calendarSync = await dependencies.syncRegistrationCalendar({
          calendar: dependencies.calendar,
          calendarId: dependencies.calendarId,
          dateInventory,
          calendarGate,
          eventRef,
          registrationReceipt: completedRegistration.receipt,
          registrationJob: completedRegistration.job,
        });
        registrations.push(dependencies.buildRegistrationCoverageEvidence({
          dateInventory,
          calendarSync,
        }));
        observedOutcomes.push(Object.freeze({ date, observed_status: "booked" }));
      }

      const registeredDates = new Set(registrations.map((item) => item.date));
      const unavailableDays = [];
      for (const day of working.days) {
        if (registeredDates.has(day.date)) continue;
        const blocked = busyInventory.busy_intervals.some((interval) => (
          interval.kind === "all_day"
          && interval.start_date <= day.date
          && day.date < interval.end_date
        ));
        if (blocked) unavailableDays.push(dependencies.proveUnavailableDay({
          busyInventory,
          date: day.date,
        }));
      }
      const coverage = dependencies.rebuildCoverage({
        tenantId,
        timeZone: working.timezone,
        now,
        registrations,
        unavailableDays,
      });
      return Object.freeze({
        coverage,
        observedOutcomes: Object.freeze(observedOutcomes),
      });
    } catch { unavailable(); }
  };
}

module.exports = { createConnectorCoverageRefreshService };
