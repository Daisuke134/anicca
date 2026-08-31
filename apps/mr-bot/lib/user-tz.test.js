"use strict";
// The shared timezone chain. H2 (diet) proved the rule and H4 (precepts) reuses it, so the rule now
// has to hold for BOTH — these tests are the thing that keeps one organ's fix from being the other
// organ's regression.
// Run: node --test lib/user-tz.test.js

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  zoneOffsetHours, localDay, localMinuteOfDay, localWeekday, resolveUserTzOffsetH,
} = require("./user-tz.js");
const { resolveDietTzOffsetH } = require("./diet-runtime.js");
const { resolvePreceptsTzOffsetH } = require("./precepts-runtime.js");

const NOON_JST = Date.parse("2026-07-27T03:00:00Z");

test("an IANA zone becomes its offset AT THAT INSTANT, so DST is the platform's problem", () => {
  assert.equal(zoneOffsetHours("Asia/Tokyo", NOON_JST), 9);
  assert.equal(zoneOffsetHours("America/New_York", NOON_JST), -4, "July is EDT, not EST");
  assert.equal(zoneOffsetHours("America/New_York", Date.parse("2026-01-15T12:00:00Z")), -5);
  assert.equal(zoneOffsetHours("UTC", NOON_JST), 0);
});

test("a zone name we cannot read is null, never a quiet fallback to Tokyo", () => {
  for (const bad of ["Mars/Olympus", "", "   ", null, undefined, 9, {}]) {
    assert.equal(zoneOffsetHours(bad, NOON_JST), null, `${JSON.stringify(bad)} must not resolve`);
  }
});

test("the local day, minute and weekday are all the USER's, including across the date line", () => {
  // 2026-07-26 15:30Z is already the 27th in Tokyo and still the 26th in UTC.
  assert.equal(localDay(Date.parse("2026-07-26T15:30:00Z"), 9), "2026-07-27");
  assert.equal(localDay(Date.parse("2026-07-26T15:30:00Z"), 0), "2026-07-26");
  assert.equal(localMinuteOfDay(NOON_JST, 9), 12 * 60);
  assert.equal(localMinuteOfDay(NOON_JST, -4), 23 * 60, "a negative offset wraps into the previous day");
  // Monday 11:00 in Tokyo is still Sunday 22:00 in New York — a "Sunday night" message that fired on
  // the UTC weekday would land on the wrong night for half the fleet.
  assert.equal(localWeekday(Date.parse("2026-07-27T02:00:00Z"), 9), 1);
  assert.equal(localWeekday(Date.parse("2026-07-27T02:00:00Z"), -4), 0);
  assert.equal(localWeekday(Date.parse("2026-07-26T14:10:00Z"), 9), 0, "23:10 JST on the 26th is Sunday");
});

test("the chain is deps → the user row's own zone → the caller's env keys → NULL", () => {
  const previous = process.env.LM_TEST_TZ_OFFSET;
  delete process.env.LM_TEST_TZ_OFFSET;
  try {
    const keys = ["LM_TEST_TZ_OFFSET"];
    assert.equal(resolveUserTzOffsetH({ tzOffsetH: -5 }, { call_time_zone: "Asia/Tokyo" }, NOON_JST, keys), -5);
    assert.equal(resolveUserTzOffsetH({}, { call_time_zone: "Asia/Tokyo" }, NOON_JST, keys), 9);
    assert.equal(resolveUserTzOffsetH({}, { time_zone: "America/New_York" }, NOON_JST, keys), -4);
    assert.equal(resolveUserTzOffsetH({}, { call_time_zone: "Mars/Olympus" }, NOON_JST, keys), null);
    assert.equal(resolveUserTzOffsetH({}, {}, NOON_JST, keys), null);
    process.env.LM_TEST_TZ_OFFSET = "2";
    assert.equal(resolveUserTzOffsetH({}, {}, NOON_JST, keys), 2);
    // An env var set to the empty string is not a zero. Falling through to UTC would put a Tokyo
    // user's bedtime question at 08:30 in the morning.
    process.env.LM_TEST_TZ_OFFSET = "";
    assert.equal(resolveUserTzOffsetH({}, {}, NOON_JST, keys), null);
    process.env.LM_TEST_TZ_OFFSET = "not-a-number";
    assert.equal(resolveUserTzOffsetH({}, {}, NOON_JST, keys), null);
  } finally {
    if (previous === undefined) delete process.env.LM_TEST_TZ_OFFSET;
    else process.env.LM_TEST_TZ_OFFSET = previous;
  }
});

test("each organ keeps its OWN env link and cannot read the other's", () => {
  const before = {
    diet: process.env.LM_DIET_UTC_OFFSET_HOURS,
    precepts: process.env.LM_PRECEPTS_UTC_OFFSET_HOURS,
  };
  try {
    process.env.LM_DIET_UTC_OFFSET_HOURS = "9";
    delete process.env.LM_PRECEPTS_UTC_OFFSET_HOURS;
    assert.equal(resolveDietTzOffsetH({}, {}, NOON_JST), 9);
    assert.equal(resolvePreceptsTzOffsetH({}, {}, NOON_JST), null,
      "the diet fallback must not silently decide when the precepts organ speaks");

    process.env.LM_PRECEPTS_UTC_OFFSET_HOURS = "-8";
    assert.equal(resolvePreceptsTzOffsetH({}, {}, NOON_JST), -8);
    assert.equal(resolveDietTzOffsetH({}, {}, NOON_JST), 9);

    // The row's own zone still outranks both env vars, for both organs.
    assert.equal(resolveDietTzOffsetH({}, { call_time_zone: "UTC" }, NOON_JST), 0);
    assert.equal(resolvePreceptsTzOffsetH({}, { call_time_zone: "UTC" }, NOON_JST), 0);
  } finally {
    for (const [key, value] of [
      ["LM_DIET_UTC_OFFSET_HOURS", before.diet], ["LM_PRECEPTS_UTC_OFFSET_HOURS", before.precepts],
    ]) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});
