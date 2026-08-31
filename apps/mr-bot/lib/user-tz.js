"use strict";
// WHOSE CLOCK. The one honest answer to "what time is it for this user", shared by every organ that
// speaks at a time of day rather than at an instant.
//
// H2 (diet) had to solve this first and solved it correctly, so H4 (precepts) does not get to solve
// it again slightly differently: two copies of a timezone chain is two chains that drift, and the
// failure mode of the drift is a message at 3am. The chain lives here once and both organs call it.
//
// The chain, in order, ENDING IN NULL rather than in a guess:
//   1. an explicit tzOffsetH from the caller (tests, and any future per-organ override)
//   2. the user row's own zone — lm_users has no tz column, so this is lm_panel_preferences
//      .call_time_zone, merged onto the row by the scheduler's user select. It is the only per-user
//      timezone that actually exists anywhere in this schema.
//   3. the organ's env fallback (LM_DIET_UTC_OFFSET_HOURS, LM_PRECEPTS_UTC_OFFSET_HOURS, …), passed
//      in by the caller so this module never has to know which organ is asking
//   4. NOTHING. The caller must stay SILENT for that user.
//
// Step 4 is the whole point. A default of JST would ask a Berlin user at 04:30 and a Los Angeles user
// at 20:00; an unasked question costs one data point, a 3am question costs the trust that makes every
// other organ tolerable.

const TZ_ROW_KEYS = Object.freeze(["call_time_zone", "time_zone", "timezone", "tz"]);

// An IANA zone name → its UTC offset in hours AT THAT INSTANT (so DST is handled by the platform's
// tz database rather than by us). Returns null for anything Intl refuses, because a zone name we
// cannot read is not evidence that the user lives in Tokyo.
function zoneOffsetHours(timeZone, atMs) {
  if (typeof timeZone !== "string" || !timeZone.trim()) return null;
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date(atMs));
    const at = Object.fromEntries(parts.filter((p) => p.type !== "literal").map((p) => [p.type, p.value]));
    const wallMs = Date.UTC(Number(at.year), Number(at.month) - 1, Number(at.day),
      Number(at.hour), Number(at.minute), Number(at.second));
    if (!Number.isFinite(wallMs)) return null;
    return (wallMs - Math.floor(atMs / 1000) * 1000) / 3600000;
  } catch {
    return null;
  }
}

// The user's LOCAL calendar day as YYYY-MM-DD. Lunch, bedtime and "this week" are all local ideas: a
// UTC day would file a 00:30 JST row under yesterday and split one person's history across two days.
function localDay(nowMs, tzOffsetH) {
  return new Date(nowMs + tzOffsetH * 3600000).toISOString().slice(0, 10);
}

// Minutes since local midnight. The modulo is taken AFTER the offset so a negative offset (the
// Americas) wraps into the previous local day instead of going negative.
function localMinuteOfDay(nowMs, tzOffsetH) {
  const localMs = nowMs + tzOffsetH * 3600000;
  const dayMs = ((localMs % 86400000) + 86400000) % 86400000;
  return Math.floor(dayMs / 60000);
}

// 0 = Sunday … 6 = Saturday, in the USER's week. Sunday in Tokyo and Sunday in Los Angeles are
// seventeen hours apart, and a weekly message that fires on the UTC weekday lands on the wrong night
// for half the fleet.
function localWeekday(nowMs, tzOffsetH) {
  return new Date(nowMs + tzOffsetH * 3600000).getUTCDay();
}

// `source` is the caller's deps or callback opts; `row` is the user row; `envKeys` are the organ's
// own env fallbacks, tried in order. An env var set to the empty string is NOT a zero — an unset-ish
// value must fall through to silence rather than silently mean UTC.
function resolveUserTzOffsetH(source = {}, row = null, nowMs = Date.now(), envKeys = []) {
  if (Number.isFinite(source && source.tzOffsetH)) return source.tzOffsetH;
  for (const key of TZ_ROW_KEYS) {
    const offsetH = zoneOffsetHours(row && row[key], nowMs);
    if (Number.isFinite(offsetH)) return offsetH;
  }
  for (const key of (Array.isArray(envKeys) ? envKeys : [envKeys])) {
    const raw = process.env[key];
    if (String(raw || "").trim() === "") continue;
    const fromEnv = Number(raw);
    if (Number.isFinite(fromEnv)) return fromEnv;
  }
  return null;
}

module.exports = {
  TZ_ROW_KEYS,
  zoneOffsetHours,
  localDay,
  localMinuteOfDay,
  localWeekday,
  resolveUserTzOffsetH,
};
