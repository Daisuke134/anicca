"use strict";

const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");
const { isVerifiedGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");

const BASE_EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;

function invalid() { throw new Error("Connector coverage refresh invalid"); }
function unavailable(code) {
  const error = new Error("Connector coverage refresh unavailable");
  if (/^CONNECTOR_COVERAGE_[A-Z_]+$/.test(String(code || ""))) error.code = code;
  throw error;
}

function inventoryUnavailable(error) {
  const code = String(error && error.code || "");
  return /^CONNECTOR_COVERAGE_INVENTORY_(?:DISCOVERY(?:_(?:PAGE(?:_(?:AUTH|TARGET))?|SNAPSHOT|ADVANCE|END_UNPROVEN))?|DETAIL|BUILD)_FAILED$/.test(code)
    ? code
    : "CONNECTOR_COVERAGE_INVENTORY_FAILED";
}

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
    "syncRegistrationCalendar",
    "buildRegistrationCoverageEvidence",
    "proveUnavailableDay",
    "rebuildCoverage",
    "planOpenDate",
    "readUnavailablePlanEvidence",
    "rebindUnavailablePlan",
  ];
  if (
    !dependencies.receiptReader
    || typeof dependencies.receiptReader.listForCoverage !== "function"
    || !dependencies.calendar
    || typeof dependencies.calendar.findConnectorEvents !== "function"
    || typeof dependencies.calendar.createConnectorEvent !== "function"
    || requiredFunctions.some((name) => typeof dependencies[name] !== "function")
    || typeof dependencies.now !== "function"
    || !String(dependencies.calendarId || "").trim()
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
        previousCoverage: current,
        registrations: [],
        unavailableDays: [],
      });
    } catch { unavailable("CONNECTOR_COVERAGE_REBUILD_FAILED"); }
    try {
      completed = await dependencies.receiptReader.listForCoverage({ tenantId, coverage: working });
    } catch { unavailable("CONNECTOR_COVERAGE_RECEIPT_READ_FAILED"); }
    if (!Array.isArray(completed)) unavailable("CONNECTOR_COVERAGE_RECEIPT_READ_FAILED");
    const requiredCanonicalUrls = [...new Set(completed.map((registration) => (
      String(registration && registration.receipt && registration.receipt.canonical_url || "").trim()
    )))];
    try {
      dateInventory = await dependencies.readDateInventory({
        coverage: working,
        now,
        requiredCanonicalUrls,
      });
    } catch (error) { unavailable(inventoryUnavailable(error)); }
    try {
      busyInventory = await dependencies.readBusyCalendar({
        calendar: dependencies.calendar,
        timeMin: midnight(working.window_start_date, working.timezone),
        timeMax: midnight(nextDate(working.window_end_date), working.timezone),
        timeZone: working.timezone,
        now,
      });
    } catch { unavailable("CONNECTOR_COVERAGE_CALENDAR_READ_FAILED"); }
    if (
      !isVerifiedRollingEventCoverage(working)
      || !isVerifiedLumaDateInventory(dateInventory)
      || dateInventory.coverage_snapshot_id !== working.coverage_snapshot_id
      || !isVerifiedGoogleCalendarBusyInventory(busyInventory)
    ) unavailable("CONNECTOR_COVERAGE_READBACK_INVALID");

    const registrations = [];
    const observedOutcomes = [];
    try {
      for (const completedRegistration of completed) {
        let eventRef;
        let date;
        let calendarSync;
        let registrationEvidence;
        try {
          eventRef = baseEventRef(completedRegistration.event_ref);
          date = eventDate(dateInventory, eventRef);
        } catch { unavailable("CONNECTOR_COVERAGE_REGISTRATION_INVENTORY_MATCH_FAILED"); }
        try {
          calendarSync = await dependencies.syncRegistrationCalendar({
            calendar: dependencies.calendar,
            calendarId: dependencies.calendarId,
            dateInventory,
            eventRef,
            registrationReceipt: completedRegistration.receipt,
            registrationJob: completedRegistration.job,
          });
        } catch { unavailable("CONNECTOR_COVERAGE_REGISTRATION_CALENDAR_SYNC_FAILED"); }
        try {
          registrationEvidence = dependencies.buildRegistrationCoverageEvidence({
            dateInventory,
            calendarSync,
          });
        } catch { unavailable("CONNECTOR_COVERAGE_REGISTRATION_EVIDENCE_FAILED"); }
        registrations.push(registrationEvidence);
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
        if (blocked) {
          try {
            unavailableDays.push(dependencies.proveUnavailableDay({
              busyInventory,
              date: day.date,
            }));
          } catch { unavailable("CONNECTOR_COVERAGE_CALENDAR_PROOF_FAILED"); }
        }
      }
      let coverage;
      try {
        coverage = dependencies.rebuildCoverage({
          tenantId,
          timeZone: working.timezone,
          now,
          previousCoverage: working,
          registrations,
          unavailableDays,
        });
      } catch { unavailable("CONNECTOR_COVERAGE_ASSEMBLY_REBUILD_FAILED"); }
      let openDatePlan;
      try {
        openDatePlan = await dependencies.planOpenDate({
          coverage,
          dateInventory,
          busyInventory,
          profile: dependencies.profile,
          apiKey: dependencies.apiKey,
        });
      } catch (error) {
        const code = String(error && error.code || "");
        unavailable(/^CONNECTOR_COVERAGE_APPLICATION_[A-Z_]+_FAILED$/.test(code)
          ? code
          : "CONNECTOR_COVERAGE_APPLICATION_PLAN_FAILED");
      }
      if (openDatePlan.status === "unavailable") {
        let unavailableEvidence;
        try {
          unavailableEvidence = dependencies.readUnavailablePlanEvidence(openDatePlan);
        } catch { unavailable("CONNECTOR_COVERAGE_UNAVAILABLE_EVIDENCE_READ_FAILED"); }
        unavailableDays.push(unavailableEvidence);
        try {
          coverage = dependencies.rebuildCoverage({
            tenantId,
            timeZone: working.timezone,
            now,
            previousCoverage: working,
            registrations,
            unavailableDays,
          });
        } catch { unavailable("CONNECTOR_COVERAGE_UNAVAILABLE_REBUILD_FAILED"); }
        try {
          openDatePlan = dependencies.rebindUnavailablePlan(openDatePlan, coverage);
        } catch { unavailable("CONNECTOR_COVERAGE_UNAVAILABLE_REBIND_FAILED"); }
        observedOutcomes.push(Object.freeze({
          date: unavailableEvidence.date,
          observed_status: "calendar_unavailable",
        }));
      }
      return Object.freeze({
        coverage,
        observedOutcomes: Object.freeze(observedOutcomes),
        openDatePlan,
      });
    } catch (error) {
      if (/^CONNECTOR_COVERAGE_[A-Z_]+$/.test(String(error && error.code || ""))) throw error;
      unavailable("CONNECTOR_COVERAGE_ASSEMBLY_FAILED");
    }
  };
}

module.exports = { createConnectorCoverageRefreshService };
