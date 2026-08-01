"use strict";

const { createHash } = require("node:crypto");

const HORIZON_DAYS = 21;
const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const DATE_KEY = /^\d{4}-\d{2}-\d{2}$/;
const RESOLVED = new Set(["covered_existing", "covered_new", "unavailable"]);
const SOURCE_REF = /^(?:evidence|provider-receipt|runtime-receipt|calendar-evidence|object):\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;
const UNSAFE = /@|\b(?:password|cookie|guest[_ -]?key|api[_ -]?key|access[_ -]?token)\b|\{\{|\}\}|\bTODO\b|\bTBD\b/i;
const VERIFIED = new WeakSet();

function invalid() { throw new Error("rolling event coverage invalid"); }

function exactInstant(value) {
  const text = String(value == null ? "" : value).trim();
  const ms = Date.parse(text);
  if (!Number.isFinite(ms) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
  return new Date(ms).toISOString();
}

function validTimeZone(value) {
  const timeZone = String(value == null ? "" : value).trim();
  if (!timeZone) invalid();
  try { new Intl.DateTimeFormat("en", { timeZone }).format(0); } catch { invalid(); }
  return timeZone;
}

function localDateKey(ms, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(ms)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function shiftDate(dateKey, days) {
  if (!DATE_KEY.test(dateKey)) invalid();
  const [year, month, day] = dateKey.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day + days));
  const result = date.toISOString().slice(0, 10);
  if (days === 0 && result !== dateKey) invalid();
  return result;
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function normalizeResolvedDay(value, allowedDates) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (Object.keys(value).sort().join(",") !== "date,evidence_refs,status") invalid();
  const date = String(value.date == null ? "" : value.date).trim();
  const status = String(value.status == null ? "" : value.status).trim();
  if (!allowedDates.has(date) || !RESOLVED.has(status)) invalid();
  if (!Array.isArray(value.evidence_refs) || value.evidence_refs.length < 1 || value.evidence_refs.length > 20) invalid();
  const evidenceRefs = value.evidence_refs.map((ref) => String(ref == null ? "" : ref).trim());
  if (new Set(evidenceRefs).size !== evidenceRefs.length || evidenceRefs.some((ref) => !SOURCE_REF.test(ref) || UNSAFE.test(ref))) invalid();
  return Object.freeze({ date, status, evidence_refs: Object.freeze(evidenceRefs) });
}

function buildRollingEventCoverage(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (!TENANT.test(tenantId)) invalid();
  const timeZone = validTimeZone(input.timeZone);
  const calculatedAt = exactInstant(input.now);
  const windowStartDate = localDateKey(Date.parse(calculatedAt), timeZone);
  const dates = Object.freeze(Array.from({ length: HORIZON_DAYS }, (_, index) => shiftDate(windowStartDate, index)));
  const allowedDates = new Set(dates);
  if (!Array.isArray(input.resolvedDays)) invalid();
  const resolved = new Map();
  for (const candidate of input.resolvedDays) {
    const day = normalizeResolvedDay(candidate, allowedDates);
    if (resolved.has(day.date)) invalid();
    resolved.set(day.date, day);
  }
  const days = Object.freeze(dates.map((date) => resolved.get(date) || Object.freeze({
    date, status: "open", evidence_refs: Object.freeze([]),
  })));
  const counts = { open: 0, covered_existing: 0, covered_new: 0, unavailable: 0 };
  for (const day of days) counts[day.status] += 1;
  const core = {
    tenant_id: tenantId,
    timezone: timeZone,
    calculated_at: calculatedAt,
    window_start_date: dates[0],
    window_end_date: dates.at(-1),
    horizon_days: HORIZON_DAYS,
    days,
    counts: Object.freeze(counts),
  };
  const digest = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const snapshot = Object.freeze({ coverage_snapshot_id: `event-coverage:${digest}`, ...core });
  VERIFIED.add(snapshot);
  return snapshot;
}

function isVerifiedRollingEventCoverage(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = { buildRollingEventCoverage, isVerifiedRollingEventCoverage };
