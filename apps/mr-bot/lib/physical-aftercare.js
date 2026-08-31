"use strict";

function blocked() {
  return {
    schema_version: 1,
    status: "blocked",
    blocker: "confirmed_booking_required",
    effects: {
      telegram_report: 0,
      calendar_event: 0,
      same_day_call_schedule: 0,
    },
  };
}

function planPhysicalAftercare({ booking } = {}) {
  if (
    booking?.status !== "booked"
    || booking.provider_confirmed !== true
    || !booking.booking_id
    || !booking.starts_at
  ) {
    return blocked();
  }
  if (Number.isNaN(Date.parse(booking.starts_at))) return blocked();
  return {
    schema_version: 1,
    status: "ready",
    booking_id: booking.booking_id,
    effects: {
      telegram_report: 1,
      calendar_event: 1,
      same_day_call_schedule: 1,
    },
  };
}

module.exports = { planPhysicalAftercare };
