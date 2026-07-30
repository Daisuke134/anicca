// honne-ja-shadow-schedule.js — the Honne JA shadow slot calendar.
//
// The legacy owner `ai.anicca.reelclaw-honne-ja` fires at StartCalendarInterval
// 12:30 and 21:30 local time (verified read-only via
// `plutil -p ~/Library/LaunchAgents/ai.anicca.reelclaw-honne-ja.plist`).
// The Life Manager shadow scheduler must encode the IDENTICAL cadence: the due
// slot for a wall-clock moment is the latest slot of the current local day that
// has already fired, expressed as the exact UTC instant of that local wall time
// so it satisfies the generation job's exact-instant slot contract.
"use strict";

const HONNE_JA_SLOTS = Object.freeze(["12:30", "21:30"]);
const SLOT_PATTERN = /^([01][0-9]|2[0-3]):([0-5][0-9])$/;

function wallClock(timeZone, date) {
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
    throw new Error("honne JA schedule time zone is invalid");
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
function zonedSlotInstant(clock, slot, timeZone) {
  const match = SLOT_PATTERN.exec(String(slot == null ? "" : slot));
  if (!match) throw new Error("honne JA schedule slot is invalid");
  if (
    !clock
    || typeof clock !== "object"
    || !Number.isInteger(clock.year)
    || !Number.isInteger(clock.month)
    || !Number.isInteger(clock.day)
    || clock.month < 1 || clock.month > 12
    || clock.day < 1 || clock.day > 31
  ) {
    throw new Error("honne JA schedule clock is invalid");
  }
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const wallUtc = Date.UTC(clock.year, clock.month - 1, clock.day, hour, minute, 0, 0);
  let instant = wallUtc;
  for (let pass = 0; pass < 2; pass += 1) {
    const seen = wallClock(timeZone, new Date(instant));
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
  const check = wallClock(timeZone, new Date(instant));
  if (
    check.year !== clock.year
    || check.month !== clock.month
    || check.day !== clock.day
    || check.hour !== hour
    || check.minute !== minute
    || check.second !== 0
  ) {
    throw new Error("honne JA schedule slot does not exist on this local day");
  }
  return new Date(instant).toISOString();
}

// The slot currently due at `nowMs` in `timeZone`: the latest HONNE_JA_SLOTS
// entry of the current local day whose wall time is <= now, as an exact UTC
// instant; null before the first slot of the local day. Every tick inside the
// same slot window resolves to the same instant, so the derived generation
// job_id is idempotent across scheduler polls.
function honneJaDueSlot(nowMs, timeZone = "Asia/Tokyo") {
  if (typeof nowMs !== "number" || !Number.isFinite(nowMs)) {
    throw new Error("honne JA schedule time is invalid");
  }
  const local = wallClock(timeZone, new Date(nowMs));
  const nowMinutes = local.hour * 60 + local.minute;
  let due = null;
  for (const slot of HONNE_JA_SLOTS) {
    const [hour, minute] = slot.split(":").map(Number);
    if (nowMinutes >= hour * 60 + minute) due = slot;
  }
  if (!due) return null;
  return zonedSlotInstant(
    { year: local.year, month: local.month, day: local.day },
    due,
    timeZone,
  );
}

module.exports = {
  HONNE_JA_SLOTS,
  honneJaDueSlot,
  zonedSlotInstant,
};
