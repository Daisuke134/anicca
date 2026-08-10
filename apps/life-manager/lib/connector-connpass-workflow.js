"use strict";

const {
  readConnpassRegistrationStateOnPage,
  submitConnpassOnPage,
} = require("./connpass-browser-provider.js");
const {
  normalizeConnpassEventDetail,
  readCalendarBindings,
  readEventDetail,
} = require("./connpass-browser-discovery.js");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const EVENT_REF = /^connpass-event:\/\/event\/[1-9][0-9]*$/;
const EVENT_URL = /^https:\/\/(?:[a-z0-9-]+\.)?connpass\.com\/event\/[1-9][0-9]*\/$/i;
const TIME_ZONE = "Asia/Tokyo";

function invalid() { throw new Error("Connpass script-first workflow invalid"); }
const DETAIL_FIELD_CODES = new Set([
  "CONNPASS_DETAIL_TITLE_INVALID_FAILED",
  "CONNPASS_DETAIL_START_INVALID_FAILED",
  "CONNPASS_DETAIL_END_INVALID_FAILED",
  "CONNPASS_DETAIL_RANGE_INVALID_FAILED",
]);

function stageError(code) {
  const error = new Error("Connpass discovery stage failed");
  error.code = code;
  return error;
}

function exactCandidate(value) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || value.provider !== "connpass"
    || !EVENT_REF.test(String(value.event_ref || ""))
    || !EVENT_URL.test(String(value.canonical_url || ""))
    || !String(value.title || "").trim()
    || !Number.isFinite(Date.parse(String(value.starts_at || "")))
    || !Number.isFinite(Date.parse(String(value.ends_at || "")))
    || Date.parse(value.starts_at) >= Date.parse(value.ends_at)
  ) invalid();
  return value;
}

function candidateWindow(now) {
  const observed = now();
  if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(observed).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return Object.freeze({
    start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)),
    end: Date.parse(zonedSlotInstant({
      year: end.getUTCFullYear(), month: end.getUTCMonth() + 1, day: end.getUTCDate(),
    }, "00:00", TIME_ZONE)),
  });
}

function discoveryDates(now) {
  const observed = now();
  if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(observed).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  const dates = [];
  for (let offset = 0; offset < 14; offset += 1) {
    const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + offset));
    dates.push(date.toISOString().slice(0, 10));
  }
  return Object.freeze(dates);
}

function createDefaultDiscovery({ now, readBindings, readDetail }) {
  return async ({ page }) => {
    if (!page || typeof page.goto !== "function") invalid();
    const dates = discoveryDates(now);
    const allowedDates = new Set(dates);
    const months = [...new Set(dates.map((date) => date.slice(0, 7).replace("-", "")))];
    if (months.length < 1 || months.length > 2) invalid();
    const bindings = [];
    const seen = new Set();
    for (const month of months) {
      try {
        await page.goto(`https://connpass.com/calendar/?ym=${month}&prefectures=13`, {
          waitUntil: "domcontentloaded", timeout: 30_000,
        });
      } catch { throw stageError("CONNPASS_CALENDAR_NAVIGATION_FAILED"); }
      let rows;
      try { rows = await readBindings(page); }
      catch { throw stageError("CONNPASS_CALENDAR_BINDINGS_FAILED"); }
      if (!Array.isArray(rows) || rows.length > 5_000) {
        throw stageError("CONNPASS_CALENDAR_ROWS_CONTRACT_FAILED");
      }
      for (const row of rows) {
        const eventRef = String(row && row.event_ref || "");
        const url = String(row && row.canonical_url || "");
        const date = String(row && row.calendar_date || "");
        if (!allowedDates.has(date) || seen.has(eventRef)) continue;
        if (!EVENT_REF.test(eventRef) || !EVENT_URL.test(url)) {
          throw stageError("CONNPASS_CALENDAR_BINDING_VALIDATION_FAILED");
        }
        seen.add(eventRef);
        bindings.push(Object.freeze({ event_ref: eventRef, canonical_url: url }));
        if (bindings.length > 500) {
          throw stageError("CONNPASS_CALENDAR_ROWS_CONTRACT_FAILED");
        }
      }
    }
    const result = [];
    for (const binding of bindings) {
      try {
        await page.goto(binding.canonical_url, { waitUntil: "domcontentloaded", timeout: 30_000 });
      } catch { throw stageError("CONNPASS_DETAIL_NAVIGATION_FAILED"); }
      let detail;
      try { detail = normalizeConnpassEventDetail(await readDetail(page)); }
      catch (error) {
        const code = String(error && error.code || "");
        throw stageError(DETAIL_FIELD_CODES.has(code) ? code : "CONNPASS_DETAIL_READ_FAILED");
      }
      if (detail.event_ref !== binding.event_ref) {
        throw stageError("CONNPASS_DETAIL_IDENTITY_MISMATCH_FAILED");
      }
      result.push(detail);
    }
    return Object.freeze(result);
  };
}

function defaultCalendarFree(candidate, calendar) {
  const intervals = Array.isArray(calendar) ? calendar
    : (calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : []);
  const start = Date.parse(candidate.starts_at);
  const end = Date.parse(candidate.ends_at);
  return !intervals.some((busy) => busy && busy.kind === "timed"
    && start < Date.parse(busy.end_at) && end > Date.parse(busy.start_at));
}

function normalizedState(value) {
  const state = String(value && (value.status || value.state) || "");
  if (["registered", "pending"].includes(state)) return Object.freeze({ status: state });
  if (state === "absent") return Object.freeze({ status: "absent" });
  return Object.freeze({ status: "unavailable" });
}

function createConnpassScriptFirstWorkflow(options = {}) {
  const now = options.now || (() => new Date());
  const readBindings = options.readCalendarBindings || readCalendarBindings;
  const readDetail = options.readEventDetail || readEventDetail;
  const discoverOnPage = options.discoverOnPage || createDefaultDiscovery({ now, readBindings, readDetail });
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const submitOnPage = options.submitOnPage || submitConnpassOnPage;
  const readStateOnPage = options.readStateOnPage || readConnpassRegistrationStateOnPage;
  const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readBindings, readDetail, discoverOnPage, isCalendarFree, submitOnPage, readStateOnPage,
    onDiscoveryAudit]
    .some((value) => typeof value !== "function")) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = await discoverOnPage({ page });
      if (!Array.isArray(observed) || observed.length > 500) {
        throw stageError("CONNPASS_DISCOVERY_RESULT_CONTRACT_FAILED");
      }
      const window = candidateWindow(now);
      const registeredExisting = [];
      const result = [];
      let normalizedCount = 0;
      let windowCount = 0;
      let freeOpenCount = 0;
      for (const raw of observed) {
        let candidate;
        try { candidate = exactCandidate(raw); }
        catch { throw stageError("CONNPASS_CANDIDATE_VALIDATION_FAILED"); }
        normalizedCount += 1;
        const startsAt = Date.parse(candidate.starts_at);
        if (startsAt < window.start || startsAt >= window.end) continue;
        windowCount += 1;
        if (candidate.registration_status === "registered") {
          registeredExisting.push(Object.freeze({ ...candidate }));
          continue;
        }
        if (candidate.registration_status !== "available") continue;
        if (candidate.ticket_price_status !== "free" || candidate.ticket_price_minor !== 0) continue;
        freeOpenCount += 1;
        let calendarFree;
        try { calendarFree = await isCalendarFree(candidate, calendar); }
        catch { throw stageError("CONNPASS_CALENDAR_CONFLICT_CHECK_FAILED"); }
        if (!calendarFree) continue;
        result.push(Object.freeze({ ...candidate }));
      }
      await onDiscoveryAudit(Object.freeze({
        observed_count: observed.length,
        normalized_count: normalizedCount,
        window_count: windowCount,
        free_open_count: freeOpenCount,
        calendar_free_count: registeredExisting.length + result.length,
      }));
      return Object.freeze([...registeredExisting, ...result]);
    },
    async runDirectAction({ page, candidate }) {
      const selected = exactCandidate(candidate);
      const outcome = await submitOnPage(page, selected);
      let currentUrl = "";
      if (outcome && ["registered", "pending"].includes(outcome.status)) {
        try {
          currentUrl = page && typeof page.url === "function" ? String(page.url()) : "";
        } catch { currentUrl = ""; }
      }
      return outcome && ["registered", "pending"].includes(outcome.status)
        && currentUrl === selected.canonical_url
        ? Object.freeze({ status: "completed", method: "connpass_direct_submit" })
        : Object.freeze({ status: "failed", safe_reason: "direct_action_unverified" });
    },
    async readProviderState({ page, candidate }) {
      exactCandidate(candidate);
      return normalizedState(await readStateOnPage(page));
    },
  });
}

module.exports = { createConnpassScriptFirstWorkflow };
