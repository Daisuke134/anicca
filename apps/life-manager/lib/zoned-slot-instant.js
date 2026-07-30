// zoned-slot-instant.js — shared local wall-clock inversion for cadence slots.
//
// Every legacy launchd owner this runtime shadows fires on a LOCAL wall clock
// (12:30/21:30 JST for Honne JA, 20:00/Sunday 20:05 JST for the financial
// report), while durable job identity has to be an exact UTC instant. Both
// schedules therefore need the same primitive: given a local calendar day and a
// local "HH:MM", return the exact UTC instant, and fail loudly when that wall
// time does not exist (DST gap) instead of silently drifting into a
// neighbouring slot.
//
// `label` prefixes every error message so each schedule keeps naming itself in
// its own failures.
"use strict";

const SLOT_PATTERN = /^([01][0-9]|2[0-3]):([0-5][0-9])$/;

// Local wall-clock fields of `date` in `timeZone`.
function zonedWallClock(timeZone, date, label = "schedule") {
  let parts;
  try {
    parts = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    }).formatToParts(date);
  } catch {
    throw new Error(`${label} time zone is invalid`);
  }
  const map = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return {
    year: Number(map.year),
    month: Number(map.month),
    day: Number(map.day),
    hour: Number(map.hour),
    minute: Number(map.minute),
    second: Number(map.second),
  };
}

// Exact UTC instant of `slot` ("HH:MM") on the local calendar day `clock`
// ({year, month, day}) in `timeZone`. Two-pass wall-clock inversion, then a
// round-trip check so a DST gap (a wall time that does not exist) fails loudly
// instead of silently drifting.
function zonedSlotInstant(clock, slot, timeZone, label = "schedule") {
  const match = SLOT_PATTERN.exec(String(slot == null ? "" : slot));
  if (!match) throw new Error(`${label} slot is invalid`);
  if (
    !clock
    || typeof clock !== "object"
    || !Number.isInteger(clock.year)
    || !Number.isInteger(clock.month)
    || !Number.isInteger(clock.day)
    || clock.month < 1 || clock.month > 12
    || clock.day < 1 || clock.day > 31
  ) {
    throw new Error(`${label} clock is invalid`);
  }
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const wallUtc = Date.UTC(clock.year, clock.month - 1, clock.day, hour, minute, 0, 0);
  let instant = wallUtc;
  for (let pass = 0; pass < 2; pass += 1) {
    const seen = zonedWallClock(timeZone, new Date(instant), label);
    const seenUtc = Date.UTC(
      seen.year,
      seen.month - 1,
      seen.day,
      seen.hour,
      seen.minute,
      seen.second,
    );
    instant += wallUtc - seenUtc;
  }
  const check = zonedWallClock(timeZone, new Date(instant), label);
  if (
    check.year !== clock.year
    || check.month !== clock.month
    || check.day !== clock.day
    || check.hour !== hour
    || check.minute !== minute
    || check.second !== 0
  ) {
    throw new Error(`${label} slot does not exist on this local day`);
  }
  return new Date(instant).toISOString();
}

// Pure calendar step backward. Date.UTC arithmetic never touches time zones, so
// walking days this way cannot skip or repeat a local day.
function previousCalendarDay(day) {
  const rolled = new Date(Date.UTC(day.year, day.month - 1, day.day) - 86400000);
  return {
    year: rolled.getUTCFullYear(),
    month: rolled.getUTCMonth() + 1,
    day: rolled.getUTCDate(),
  };
}

// Weekday of a local calendar day, 0 = Sunday (matches Date#getUTCDay).
function calendarWeekday(day) {
  return new Date(Date.UTC(day.year, day.month - 1, day.day)).getUTCDay();
}

module.exports = {
  SLOT_PATTERN,
  calendarWeekday,
  previousCalendarDay,
  zonedSlotInstant,
  zonedWallClock,
};
