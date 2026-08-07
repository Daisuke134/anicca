"use strict";

const {
  readConnpassRegistrationStateOnPage,
  submitConnpassOnPage,
} = require("./connpass-browser-provider.js");
const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const EVENT_REF = /^connpass-event:\/\/event\/[1-9][0-9]*$/;
const EVENT_URL = /^https:\/\/(?:[a-z0-9-]+\.)?connpass\.com\/event\/[1-9][0-9]*\/$/i;
const TIME_ZONE = "Asia/Tokyo";

function invalid() { throw new Error("Connpass script-first workflow invalid"); }

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
  const discoverOnPage = options.discoverOnPage;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const submitOnPage = options.submitOnPage || submitConnpassOnPage;
  const readStateOnPage = options.readStateOnPage || readConnpassRegistrationStateOnPage;
  if ([now, discoverOnPage, isCalendarFree, submitOnPage, readStateOnPage]
    .some((value) => typeof value !== "function")) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      const observed = await discoverOnPage({ page });
      if (!Array.isArray(observed) || observed.length > 500) invalid();
      const window = candidateWindow(now);
      const result = [];
      for (const raw of observed) {
        const candidate = exactCandidate(raw);
        const startsAt = Date.parse(candidate.starts_at);
        if (startsAt < window.start || startsAt >= window.end) continue;
        if (candidate.registration_status !== "available") continue;
        if (candidate.ticket_price_status !== "free" || candidate.ticket_price_minor !== 0) continue;
        if (!await isCalendarFree(candidate, calendar)) continue;
        result.push(Object.freeze({ ...candidate }));
      }
      return Object.freeze(result);
    },
    async runDirectAction({ page, candidate }) {
      const outcome = await submitOnPage(page, exactCandidate(candidate));
      return outcome && ["registered", "pending"].includes(outcome.status)
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
