"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { planPhysicalAftercare } = require("./physical-aftercare");

test("confirmed booking plans Telegram, calendar, and same-day call wiring", () => {
  const plan = planPhysicalAftercare({
    booking: {
      status: "booked",
      booking_id: "provider-booking-id",
      provider_confirmed: true,
      starts_at: "2026-08-03T09:30:00+09:00",
    },
  });
  assert.deepEqual(plan, {
    schema_version: 1,
    status: "ready",
    booking_id: "provider-booking-id",
    effects: {
      telegram_report: 1,
      calendar_event: 1,
      same_day_call_schedule: 1,
    },
  });
});

test("unconfirmed booking blocks all downstream claims and side effects", () => {
  assert.deepEqual(planPhysicalAftercare({
    booking: {
      status: "honest_failure_reported",
      booking_id: null,
      provider_confirmed: false,
    },
  }), {
    schema_version: 1,
    status: "blocked",
    blocker: "confirmed_booking_required",
    effects: {
      telegram_report: 0,
      calendar_event: 0,
      same_day_call_schedule: 0,
    },
  });
});

test("a tentative slot, prior failure report, or fabricated booking id cannot satisfy the gate", () => {
  for (const booking of [
    { status: "slot_selected", booking_id: null, provider_confirmed: false },
    { status: "honest_failure_reported", booking_id: null, provider_confirmed: false },
    { status: "booked", booking_id: "invented", provider_confirmed: false },
  ]) {
    assert.equal(planPhysicalAftercare({ booking }).status, "blocked");
  }
});
