// financial-report-schedule.js — the financial report CADENCE calendar.
//
// The legacy owner `ai.anicca.life-manager-financial-report` is a
// `StartInterval = 300` poll (verified read-only via
// `plutil -p ~/Library/LaunchAgents/ai.anicca.life-manager-financial-report.plist`),
// but the poll interval is NOT the cadence: the boot script only ACTS when the
// report is due, and skips with `not_due` otherwise (measured in
// `~/.anicca/logs/life-manager-financial-report.out.log`: 736 `not_due` skips
// against 1 real send). The real cadence is the release window encoded by
// `dueReportKinds` in `financial-report-runtime.js`:
//
//   daily  — every local day from 20:00 local time
//   weekly — Sunday only, from 20:05 local time
//
// This module is the single source of truth for that cadence. Anchoring job
// identity to a cadence SLOT (the exact UTC instant of the local release wall
// time) instead of to poll time is what makes the enqueue idempotent: every
// poll inside one due window derives the same slot, therefore the same
// `job_id`/`effect_key`, therefore at most one durable job per due period.
"use strict";

const { periodBounds } = require("./financial-report-snapshot.js");
const {
  calendarWeekday,
  previousCalendarDay,
  zonedSlotInstant,
  zonedWallClock,
} = require("./zoned-slot-instant.js");

const LABEL = "financial report schedule";

// weekday: null = every local day, 0 = Sunday only (Date#getUTCDay numbering).
const FINANCIAL_REPORT_SLOTS = Object.freeze([
  Object.freeze({ kind: "daily", time: "20:00", weekday: null }),
  Object.freeze({ kind: "weekly", time: "20:05", weekday: 0 }),
]);

// How far back the grid walk searches for the previous expected run. The
// sparsest cadence entry is weekly, so 8 local days always contains one.
const MAX_GRID_LOOKBACK_DAYS = 8;

function slotDefinition(kind) {
  const definition = FINANCIAL_REPORT_SLOTS.find((entry) => entry.kind === kind);
  if (!definition) throw new Error(`${LABEL} kind is invalid`);
  return definition;
}

function localClock(nowMs, timeZone) {
  const instant = Number(nowMs);
  if (!Number.isFinite(instant)) throw new Error(`${LABEL} time is invalid`);
  const clock = zonedWallClock(timeZone, new Date(instant), LABEL);
  return {
    ...clock,
    weekday: calendarWeekday(clock),
    minuteOfDay: clock.hour * 60 + clock.minute,
  };
}

function slotMinuteOfDay(definition) {
  const [hour, minute] = definition.time.split(":").map(Number);
  return hour * 60 + minute;
}

function slotFiresOnDay(definition, weekday) {
  return definition.weekday == null || definition.weekday === weekday;
}

// Exact UTC instant of `kind`'s slot on the local calendar day `day`
// ({year, month, day}). Throws when the kind never fires on that weekday, so a
// caller can never silently invent a weekly slot on a Tuesday.
function financialReportSlotInstant(kind, day, timeZone) {
  const definition = slotDefinition(kind);
  if (
    !day
    || typeof day !== "object"
    || !Number.isInteger(day.year)
    || !Number.isInteger(day.month)
    || !Number.isInteger(day.day)
  ) {
    throw new Error(`${LABEL} local day is invalid`);
  }
  if (!slotFiresOnDay(definition, calendarWeekday(day))) {
    throw new Error(`${LABEL} has no ${kind} slot on this local day`);
  }
  return zonedSlotInstant(day, definition.time, timeZone, LABEL);
}

// The report kinds whose release window is open at `nowMs`. This is the same
// window `financial-report-runtime.js` enforces, kept here so the scheduler and
// the runtime cannot drift apart.
function dueFinancialReportKinds(nowMs, timeZone) {
  const clock = localClock(nowMs, timeZone);
  return FINANCIAL_REPORT_SLOTS
    .filter((definition) => (
      slotFiresOnDay(definition, clock.weekday)
      && clock.minuteOfDay >= slotMinuteOfDay(definition)
    ))
    .map(({ kind }) => kind);
}

// The due cadence slots at `nowMs`: one entry per kind whose window is open,
// each carrying the exact slot instant of the CURRENT local day. Two polls
// inside one window return identical entries.
function dueFinancialReportSlots(nowMs, timeZone) {
  const clock = localClock(nowMs, timeZone);
  const day = { year: clock.year, month: clock.month, day: clock.day };
  return dueFinancialReportKinds(nowMs, timeZone).map((kind) => ({
    kind,
    slot: financialReportSlotInstant(kind, day, timeZone),
  }));
}

// The latest `kind` slot at or before `beforeMs`, walking back over local
// calendar days. A slot that does not exist on a local day (DST gap) is skipped:
// it was never expected to fire.
function latestFinancialReportSlot(kind, beforeMs, timeZone) {
  const definition = slotDefinition(kind);
  const clock = localClock(beforeMs, timeZone);
  let day = { year: clock.year, month: clock.month, day: clock.day };
  for (let index = 0; index <= MAX_GRID_LOOKBACK_DAYS; index += 1) {
    if (slotFiresOnDay(definition, calendarWeekday(day))) {
      let instant;
      try {
        instant = zonedSlotInstant(day, definition.time, timeZone, LABEL);
      } catch {
        instant = null;
      }
      if (instant && Date.parse(instant) <= Number(beforeMs)) return instant;
    }
    day = previousCalendarDay(day);
  }
  return null;
}

// The latest EXPECTED RUN at or before `beforeMs` across the whole cadence
// grid (daily and weekly interleaved), as {kind, slot, period_key}. Walking
// `latestFinancialReportRun(Date.parse(slot) - 1)` yields the previous expected
// run, so the entire expected sequence is derivable backward from any instant.
function latestFinancialReportRun(beforeMs, timeZone) {
  const candidates = FINANCIAL_REPORT_SLOTS
    .map(({ kind }) => ({
      kind,
      slot: latestFinancialReportSlot(kind, beforeMs, timeZone),
    }))
    .filter(({ slot }) => slot != null);
  if (candidates.length < 1) return null;
  const latest = candidates.reduce((best, candidate) => (
    Date.parse(candidate.slot) > Date.parse(best.slot) ? candidate : best
  ));
  return {
    kind: latest.kind,
    slot: latest.slot,
    period_key: periodBounds({
      kind: latest.kind,
      nowMs: Date.parse(latest.slot),
      timezone: timeZone,
    }).period_key,
  };
}

// The cadence slot instant of a report PERIOD KEY ("2026-08-05" for daily,
// "2026-W31" for weekly). Needed to place rows that carry only a period key —
// the legacy send ledger keys receipts by (uid, report_kind, period_key) — onto
// the same expected-run grid as durable shadow receipts.
function financialReportSlotForPeriodKey(kind, periodKey, timeZone) {
  const key = String(periodKey == null ? "" : periodKey).trim();
  slotDefinition(kind);
  if (kind === "daily") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
    if (!match) throw new Error(`${LABEL} daily period key is invalid`);
    return financialReportSlotInstant("daily", {
      year: Number(match[1]),
      month: Number(match[2]),
      day: Number(match[3]),
    }, timeZone);
  }
  const match = /^(\d{4})-W(\d{2})$/.exec(key);
  if (!match) throw new Error(`${LABEL} weekly period key is invalid`);
  const isoYear = Number(match[1]);
  const isoWeek = Number(match[2]);
  if (isoWeek < 1 || isoWeek > 53) throw new Error(`${LABEL} weekly period key is invalid`);
  // ISO-8601: week 1 is the week containing January 4th.
  const january4 = Date.UTC(isoYear, 0, 4);
  const weekdayOfJanuary4 = new Date(january4).getUTCDay() || 7;
  const firstMonday = january4 - (weekdayOfJanuary4 - 1) * 86400000;
  // The weekly report fires on the SUNDAY that closes the ISO week.
  const sunday = new Date(firstMonday + ((isoWeek - 1) * 7 + 6) * 86400000);
  return financialReportSlotInstant("weekly", {
    year: sunday.getUTCFullYear(),
    month: sunday.getUTCMonth() + 1,
    day: sunday.getUTCDate(),
  }, timeZone);
}

// True only when `ms` is EXACTLY a cadence slot instant for `kind`. Used to
// separate legitimate cadence-anchored jobs from off-cadence litter.
function isFinancialReportSlotInstant(kind, ms, timeZone) {
  const instant = Number(ms);
  if (!Number.isFinite(instant)) return false;
  let definition;
  try {
    definition = slotDefinition(kind);
  } catch {
    return false;
  }
  let clock;
  try {
    clock = localClock(instant, timeZone);
  } catch {
    return false;
  }
  if (!slotFiresOnDay(definition, clock.weekday)) return false;
  let expected;
  try {
    expected = zonedSlotInstant(
      { year: clock.year, month: clock.month, day: clock.day },
      definition.time,
      timeZone,
      LABEL,
    );
  } catch {
    return false;
  }
  return Date.parse(expected) === instant;
}

module.exports = {
  FINANCIAL_REPORT_SLOTS,
  dueFinancialReportKinds,
  dueFinancialReportSlots,
  financialReportSlotForPeriodKey,
  financialReportSlotInstant,
  isFinancialReportSlotInstant,
  latestFinancialReportRun,
  latestFinancialReportSlot,
};
