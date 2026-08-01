"use strict";

const { createHash } = require("node:crypto");

const STATUSES = Object.freeze(["covered_existing", "covered_new", "unavailable"]);
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const EVIDENCE = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;

function invalid(label) { throw new Error(`rolling event coverage ${label} invalid`); }

function localDateAt(instant, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(instant);
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function addDays(date, days) {
  const [year, month, day] = date.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1, day + days));
  return value.toISOString().slice(0, 10);
}

function buildRollingEventCoverage(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (!tenantId || tenantId.length > 128) invalid("tenant");
  const nowRaw = String(input.now == null ? "" : input.now).trim();
  const nowMs = Date.parse(nowRaw);
  if (!Number.isFinite(nowMs) || !/[zZ]|[+-]\d\d:\d\d$/.test(nowRaw)) invalid("now");
  const timeZone = String(input.timeZone || "Asia/Tokyo").trim();
  let start;
  try { start = localDateAt(new Date(nowMs), timeZone); } catch { invalid("timezone"); }
  const end = addDays(start, 20);
  if (!Array.isArray(input.observations)) invalid("observations");
  const observations = new Map();
  for (const observation of input.observations) {
    if (!observation || typeof observation !== "object" || Array.isArray(observation)) invalid("observation");
    const date = String(observation.date || "").trim();
    const status = String(observation.status || "").trim();
    const evidenceRef = String(observation.evidence_ref || "").trim();
    if (!DATE.test(date) || !STATUSES.includes(status)) invalid("observation");
    if (!EVIDENCE.test(evidenceRef)) invalid("evidence");
    if (observations.has(date)) invalid("duplicate observation");
    observations.set(date, Object.freeze({ status, evidence_ref: evidenceRef }));
  }
  const counts = { covered_existing: 0, covered_new: 0, unavailable: 0, open: 0 };
  const days = [];
  for (let index = 0; index < 21; index += 1) {
    const date = addDays(start, index);
    const current = observations.get(date);
    const status = current ? current.status : "open";
    counts[status] += 1;
    days.push(Object.freeze({
      date,
      status,
      evidence_ref: current ? current.evidence_ref : null,
    }));
  }
  const goalId = `event-coverage:${createHash("sha256").update(`${tenantId}\n${timeZone}\n${start}\n${end}`).digest("hex")}`;
  return Object.freeze({
    schema_version: 1,
    goal_id: goalId,
    tenant_id: tenantId,
    timezone: timeZone,
    calculated_at: new Date(nowMs).toISOString(),
    window_start: start,
    window_end: end,
    days: Object.freeze(days),
    counts: Object.freeze(counts),
    open_count: counts.open,
    complete: counts.open === 0,
  });
}

module.exports = { buildRollingEventCoverage };
