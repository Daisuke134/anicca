"use strict";

const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const SEARCH_URL = "https://peatix.com/search?q=%E7%84%A1%E6%96%99&country=JP&l.text=Tokyo";
const TIME_ZONE = "Asia/Tokyo";
const EVENT_ID = /^[1-9][0-9]*$/;
const EVENT_PATH = /^\/event\/([1-9][0-9]*)\/?$/;
const EVENT_URL = /^https:\/\/peatix\.com\/event\/([1-9][0-9]*)\/?$/i;
const SAFE_CODES = new Set([
  "PEATIX_SEARCH_NAVIGATION_FAILED",
  "PEATIX_SEARCH_READ_FAILED",
  "PEATIX_SEARCH_ROWS_CONTRACT_FAILED",
  "PEATIX_DETAIL_NAVIGATION_FAILED",
  "PEATIX_DETAIL_READ_FAILED",
  "PEATIX_DETAIL_IDENTITY_MISMATCH_FAILED",
  "PEATIX_CANDIDATE_VALIDATION_FAILED",
  "PEATIX_CALENDAR_CONFLICT_CHECK_FAILED",
]);

function invalid() {
  throw new Error("Peatix discovery workflow invalid");
}

function stageError(code) {
  const error = new Error("Peatix discovery stage failed");
  error.code = code;
  return error;
}

function preserveSafe(error, fallback) {
  const code = String(error && error.code || "");
  return stageError(SAFE_CODES.has(code) ? code : fallback);
}

function eventId(value) {
  const id = String(value == null ? "" : value);
  return EVENT_ID.test(id) ? id : null;
}

function eventUrlId(value) {
  let url;
  try { url = new URL(String(value == null ? "" : value).trim()); } catch { return null; }
  if (url.protocol !== "https:" || url.hostname.toLowerCase() !== "peatix.com"
    || url.username || url.password) return null;
  const match = EVENT_PATH.exec(url.pathname);
  return match ? match[1] : null;
}

function canonicalBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const rawUrl = String(row.canonical_url || row.href || row.url || "");
  const id = eventUrlId(rawUrl);
  if (!id) return null;
  const expectedRef = `peatix-event://event/${id}`;
  if (row.event_ref != null && String(row.event_ref) !== expectedRef) return null;
  const title = String(row.title || "").trim();
  return Object.freeze({
    event_ref: expectedRef,
    canonical_url: `https://peatix.com/event/${id}`,
    ...(title ? { title } : {}),
  });
}

function localParts(value) {
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) invalid();
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value).filter((part) => part.type !== "literal")
    .map((part) => [part.type, Number(part.value)]));
  if (![parts.year, parts.month, parts.day].every(Number.isInteger)) invalid();
  return parts;
}

function candidateWindow(observed) {
  const parts = localParts(observed);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return Object.freeze({
    start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)),
    end: Date.parse(zonedSlotInstant({
      year: end.getUTCFullYear(),
      month: end.getUTCMonth() + 1,
      day: end.getUTCDate(),
    }, "00:00", TIME_ZONE)),
  });
}

function parseTokyoDate(value) {
  const raw = String(value == null ? "" : value).trim();
  const wall = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/
    .exec(raw);
  if (wall) {
    const [, year, month, day, hour, minute, seconds = "0", fraction = "0"] = wall;
    if (Number(seconds) > 59) return null;
    try {
      const base = Date.parse(zonedSlotInstant({
        year: Number(year), month: Number(month), day: Number(day),
      }, `${hour}:${minute}`, TIME_ZONE));
      const milliseconds = Number((fraction + "000").slice(0, 3));
      return new Date(base + Number(seconds) * 1000 + milliseconds).toISOString();
    } catch {
      return null;
    }
  }
  if (!/(?:Z|[+-][0-9]{2}:[0-9]{2})$/i.test(raw)) return null;
  const parsed = Date.parse(raw);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
}

function exactCandidate(value) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || value.provider !== "peatix"
    || !/^peatix-event:\/\/event\/[1-9][0-9]*$/.test(String(value.event_ref || ""))
    || !EVENT_URL.test(String(value.canonical_url || ""))
    || !String(value.title || "").trim()
    || !["available", "closed"].includes(value.registration_status)
    || !["free", "paid"].includes(value.ticket_price_status)
    || !Number.isInteger(value.ticket_price_minor) || value.ticket_price_minor < 0
    || !Number.isFinite(Date.parse(String(value.starts_at || "")))
    || !Number.isFinite(Date.parse(String(value.ends_at || "")))
    || Date.parse(value.starts_at) >= Date.parse(value.ends_at)
  ) invalid();
  return value;
}

function firstText(...values) {
  for (const value of values) {
    const text = String(value == null ? "" : value).trim();
    if (text) return text;
  }
  return "";
}

function numericMinor(tickets) {
  const prices = tickets
    .map((ticket) => ticket && ticket.price)
    .filter((price) => Number.isInteger(price) && price >= 0);
  return prices.length ? Math.min(...prices) : 0;
}

function usableFreeTicket(ticket, nowMs) {
  if (!ticket || typeof ticket !== "object" || Array.isArray(ticket)) return false;
  if (ticket.price !== 0 || ticket.status !== 10) return false;
  if (!Number.isInteger(ticket.seatsAvailable) || ticket.seatsAvailable <= 0) return false;
  const deadline = ticket.salesEnds && ticket.salesEnds.datetime;
  if (deadline == null || String(deadline).trim() === "") return true;
  const deadlineIso = parseTokyoDate(deadline);
  return deadlineIso != null && Date.parse(deadlineIso) > nowMs;
}

function normalizeDetail(binding, raw, nowMs) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) invalid();
  const event = raw.event;
  if (!event || typeof event !== "object" || Array.isArray(event)) invalid();
  const detailId = eventId(event.id);
  if (!detailId) invalid();
  const bindingId = binding.event_ref.split("/").pop();
  if (detailId !== bindingId) throw stageError("PEATIX_DETAIL_IDENTITY_MISMATCH_FAILED");
  const startsAt = parseTokyoDate(event.datetime ?? raw.datetime);
  const endsAt = parseTokyoDate(event.datetimeEnd ?? raw.datetimeEnd);
  if (!startsAt || !endsAt || Date.parse(startsAt) >= Date.parse(endsAt)) invalid();
  const tickets = event.tickets ?? raw.tickets;
  if (!Array.isArray(tickets)) invalid();
  const title = firstText(event.title, event.name, raw.title, raw.name, binding.title);
  if (!title) invalid();
  const freeObserved = tickets.some((ticket) => ticket && ticket.price === 0);
  const freeOpen = (event.status ?? raw.status) === "OPEN"
    && (event.isOpen ?? raw.isOpen) === true
    && (event.isFinished ?? raw.isFinished) !== true
    && tickets.some((ticket) => usableFreeTicket(ticket, nowMs));
  const candidate = Object.freeze({
    provider: "peatix",
    event_ref: binding.event_ref,
    canonical_url: binding.canonical_url,
    title,
    starts_at: startsAt,
    ends_at: endsAt,
    registration_status: freeOpen ? "available" : "closed",
    ticket_price_status: freeObserved ? "free" : "paid",
    ticket_price_minor: freeObserved ? 0 : numericMinor(tickets),
  });
  exactCandidate(candidate);
  return Object.freeze({ candidate, free_open: freeOpen });
}

function defaultCalendarFree(candidate, calendar) {
  const intervals = Array.isArray(calendar)
    ? calendar
    : (calendar && Array.isArray(calendar.busy_intervals) ? calendar.busy_intervals : []);
  const start = Date.parse(candidate.starts_at);
  const end = Date.parse(candidate.ends_at);
  return !intervals.some((busy) => (
    busy && busy.kind === "timed"
    && start < Date.parse(busy.end_at)
    && end > Date.parse(busy.start_at)
  ));
}

async function defaultReadSearchBindings(page) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  try {
    await page.goto(SEARCH_URL, { waitUntil: "domcontentloaded", timeout: 30_000 });
  } catch {
    throw stageError("PEATIX_SEARCH_NAVIGATION_FAILED");
  }
  try {
    return await page.evaluate(() => Array.from(document.querySelectorAll("a.event-card"))
      .map((anchor) => ({ href: anchor.href, title: anchor.textContent.trim() })));
  } catch {
    throw stageError("PEATIX_SEARCH_READ_FAILED");
  }
}

async function defaultReadEventViewData(page, canonicalUrl) {
  if (!page || typeof page.goto !== "function" || typeof page.evaluate !== "function") invalid();
  try {
    await page.goto(canonicalUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  } catch {
    throw stageError("PEATIX_DETAIL_NAVIGATION_FAILED");
  }
  try {
    return await page.evaluate(async (url) => {
      const response = await fetch(`${url}/get_view_data`, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Peatix event JSON response failed");
      return response.json();
    }, canonicalUrl);
  } catch {
    throw stageError("PEATIX_DETAIL_READ_FAILED");
  }
}

function createPeatixDiscoveryWorkflow(options = {}) {
  const now = options.now || (() => new Date());
  const readSearchBindings = options.readSearchBindings || defaultReadSearchBindings;
  const readEventViewData = options.readEventViewData || defaultReadEventViewData;
  const isCalendarFree = options.isCalendarFree || defaultCalendarFree;
  const onDiscoveryAudit = options.onDiscoveryAudit || (() => {});
  if ([now, readSearchBindings, readEventViewData, isCalendarFree, onDiscoveryAudit]
    .some((value) => typeof value !== "function")) invalid();

  return Object.freeze({
    async discoverCandidates({ page, calendar }) {
      if (!page || typeof page !== "object" || Array.isArray(page)) {
        throw stageError("PEATIX_PAGE_VALIDATION_FAILED");
      }
      let rows;
      try {
        rows = await readSearchBindings(page);
      } catch (error) {
        throw preserveSafe(error, "PEATIX_SEARCH_READ_FAILED");
      }
      if (!Array.isArray(rows) || rows.length > 100) {
        throw stageError("PEATIX_SEARCH_ROWS_CONTRACT_FAILED");
      }
      const bindings = [];
      const seen = new Set();
      for (const row of rows) {
        const binding = canonicalBinding(row);
        if (!binding || seen.has(binding.event_ref)) continue;
        seen.add(binding.event_ref);
        bindings.push(binding);
      }

      const observed = now();
      const window = candidateWindow(observed);
      const nowMs = observed.getTime();
      const result = [];
      let normalizedCount = 0;
      let windowCount = 0;
      let freeOpenCount = 0;
      for (const binding of bindings) {
        let raw;
        try {
          raw = await readEventViewData(page, binding.canonical_url);
        } catch (error) {
          throw preserveSafe(error, "PEATIX_DETAIL_READ_FAILED");
        }
        let normalized;
        try {
          normalized = normalizeDetail(binding, raw, nowMs);
        } catch (error) {
          if (String(error && error.code || "") === "PEATIX_DETAIL_IDENTITY_MISMATCH_FAILED") {
            throw error;
          }
          throw stageError("PEATIX_CANDIDATE_VALIDATION_FAILED");
        }
        normalizedCount += 1;
        const startsAt = Date.parse(normalized.candidate.starts_at);
        if (startsAt < window.start || startsAt >= window.end) continue;
        windowCount += 1;
        if (!normalized.free_open) continue;
        freeOpenCount += 1;
        let calendarFree;
        try {
          calendarFree = await isCalendarFree(normalized.candidate, calendar);
        } catch {
          throw stageError("PEATIX_CALENDAR_CONFLICT_CHECK_FAILED");
        }
        if (!calendarFree) continue;
        result.push(Object.freeze({ ...normalized.candidate }));
      }
      const audit = Object.freeze({
        observed_count: bindings.length,
        normalized_count: normalizedCount,
        window_count: windowCount,
        free_open_count: freeOpenCount,
        calendar_free_count: result.length,
      });
      await onDiscoveryAudit(audit);
      return Object.freeze(result);
    },
  });
}

module.exports = { createPeatixDiscoveryWorkflow };
