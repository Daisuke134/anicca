"use strict";

const { zonedSlotInstant } = require("./honne-ja-shadow-schedule.js");

const TIME_ZONE = "Asia/Tokyo";
const EVENT_URL = /^https:\/\/www\.kokuchpro\.com\/event\/([0-9a-f]{32})(?:\/([1-9][0-9]{0,19}))?\/$/;
const ISO_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})$/;
const CONTROL = /[\u0000-\u001F\u007F-\u009F]/;

function invalid() { throw new Error("KokuchPro workflow invalid"); }

function exactUrl(value) {
  if (typeof value !== "string") return null;
  const match = EVENT_URL.exec(value);
  return match ? Object.freeze({ canonical_url: value, event_key: match[1], occurrence_id: match[2] || null }) : null;
}

function canonicalKokuchProBinding(value) {
  const row = typeof value === "string" ? { canonical_url: value } : value;
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const urlValues = ["canonical_url", "href", "url"].filter((key) => Object.hasOwn(row, key)).map((key) => row[key]);
  if (!urlValues.length || urlValues.some((raw) => typeof raw !== "string" || raw !== urlValues[0])) return null;
  const parsed = exactUrl(urlValues[0]);
  if (!parsed) return null;
  const eventRef = `kokuchpro-event://event/${parsed.event_key}${parsed.occurrence_id ? `/${parsed.occurrence_id}` : ""}`;
  if (Object.hasOwn(row, "event_ref") && row.event_ref !== eventRef) return null;
  if (Object.hasOwn(row, "event_key") && row.event_key !== parsed.event_key) return null;
  if (Object.hasOwn(row, "occurrence_id") && row.occurrence_id !== parsed.occurrence_id) return null;
  return Object.freeze({ event_ref: eventRef, canonical_url: parsed.canonical_url });
}

function localParts(value) {
  if (!(value instanceof Date) || !Number.isFinite(value.getTime())) invalid();
  return Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(value).filter((part) => part.type !== "literal").map((part) => [part.type, Number(part.value)]));
}

function candidateWindow(now) {
  const parts = localParts(now);
  const end = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + 14));
  return { start: Date.parse(zonedSlotInstant(parts, "00:00", TIME_ZONE)), end: Date.parse(zonedSlotInstant({
    year: end.getUTCFullYear(), month: end.getUTCMonth() + 1, day: end.getUTCDate(),
  }, "00:00", TIME_ZONE)) };
}

function publicText(value, max) {
  return typeof value === "string" && value.length > 0 && value.length <= max
    && value === value.trim() && !CONTROL.test(value) ? value : null;
}

function parseIso(value) {
  const match = typeof value === "string" ? ISO_TIME.exec(value) : null;
  if (!match) return NaN;
  const [year, month, day, hour, minute] = match.slice(1, 6).map(Number);
  const second = Number(match[6] || 0);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) return NaN;
  const base = new Date(0); base.setUTCFullYear(year, month - 1, day); base.setUTCHours(hour, minute, second, Number((match[7] || "").padEnd(3, "0")) || 0);
  if (!Number.isFinite(base.getTime())) return NaN;
  const zone = match[8];
  if (zone === "Z") return base.getTime();
  const zoneHour = Number(zone.slice(1, 3)); const zoneMinute = Number(zone.slice(4, 6));
  if (zoneHour > 23 || zoneMinute > 59) return NaN;
  const offset = (zone[0] === "+" ? 1 : -1) * (zoneHour * 60 + zoneMinute);
  return base.getTime() - offset * 60_000;
}

function normalizeKokuchProDetail(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const { binding, detail, now } = input;
  const selected = canonicalKokuchProBinding(binding);
  if (!selected) invalid();
  const parsed = exactUrl(selected.canonical_url);
  const detailUrls = ["canonical_url", "href", "url"].filter((key) => Object.hasOwn(detail || {}, key));
  if (!detail || typeof detail !== "object" || Array.isArray(detail)
    || detailUrls.some((key) => detail[key] !== selected.canonical_url)
    || !Object.hasOwn(detail, "canonical_url")
    || (Object.hasOwn(detail, "event_ref") && detail.event_ref !== selected.event_ref)
    || detail.event_key !== parsed.event_key
    || detail.occurrence_id !== parsed.occurrence_id) invalid();

  const title = publicText(detail.title, 500);
  const venue = publicText(detail.venue, 1000);
  const address = publicText(detail.address, 1000);
  const starts = parseIso(detail.starts_at);
  const ends = parseIso(detail.ends_at);
  if (!title || !venue || !address || !Number.isFinite(starts) || !Number.isFinite(ends)) return null;
  if (detail.event_format !== "offline" || detail.fee_scheme !== "free"
    || detail.registration_status !== "open" || detail.is_full !== false
    || !address.startsWith("東京都")) return null;
  const tickets = detail.tickets;
  const ticket = Array.isArray(tickets) && tickets.length === 1 ? tickets[0] : null;
  const ticketId = ticket && typeof ticket.id === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(ticket.id)
    ? ticket.id : null;
  if (!ticket || typeof ticket !== "object" || Array.isArray(ticket)
    || !ticketId
    || ticket.status !== "available" || ticket.price_currency !== "JPY" || ticket.price_minor !== 0) return null;
  const window = candidateWindow(now);
  if (ends <= starts || starts < window.start || starts >= window.end) return null;
  return Object.freeze({ provider: "kokuchpro", event_ref: selected.event_ref, canonical_url: selected.canonical_url,
    title, starts_at: new Date(starts).toISOString(), ends_at: new Date(ends).toISOString(), venue, address,
    registration_status: "available", ticket_id: ticketId, ticket_price_status: "free", ticket_price_minor: 0 });
}

module.exports = { canonicalKokuchProBinding, normalizeKokuchProDetail };
