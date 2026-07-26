"use strict";
// lib/care-aftercare.js — 11d: what happens AFTER 11c tries to book.
//
// §9.5 REPORT, DON'T ASK: the user is told what was done, not asked for permission. That cuts both
// ways — a booking that happened is reported as a booking (§9.11 PHYSICAL copy, verbatim from
// lib/i18n.js), and a booking that did NOT happen is reported as a failure with the real candidates
// attached, never as silence and never as a hedged half-success.
//
// Three outcomes, three different shapes, and the difference between them is the whole point:
//
//   booked          → §9.11 事後報告 + a real calendar event + the booking on the scan row. The
//                     sentence 「カレンダーに入れてあります」 is rendered from the RESULT of that
//                     write, never alongside it: no calendar, a refused write, or a slot with no
//                     timezone all produce the sentence that says the entry could not be made.
//   possibly_booked → an honest "I could not confirm it, and I did not resend" message.
//                     NO calendar event: writing 木曜18:00 into someone's calendar off an
//                     unconfirmed submit is exactly the fabricated success 11d was blocked on before.
//   honest_failure  → §9.5's 候補提示 + 正直報告: why I could not book, and the real candidates 11b
//                     found so the user can finish it in one tap of their own.
//
// The record is written for ALL THREE, even when the user is unreachable and even when the send
// fails — the scan row is the audit trail, and an attempt that left no trace is indistinguishable
// from an attempt that never happened. It nests under `chain.booking` because lm_care_scan_log's
// append-only trigger permits exactly two columns to be filled in after insert: chain, chain_error.

const { formatCareBookingReport } = require("./i18n.js");

// Google Calendar via the transport wants a naive local datetime + a timezone name. travel.js's
// createTravelBlock settled this the same way: normalise to UTC and say so, rather than guessing a
// tz name from an offset. The event is one hour long because no provider readback we have gives a
// duration — an hour is the block the user should hold, not a claim about the appointment's length.
function isoNaiveUTC(ms) {
  return new Date(ms).toISOString().slice(0, 19);
}

// A slot string with no UTC offset — "2026-08-08T11:00" — is NOT a moment in time. Date.parse reads
// it in whatever timezone the SERVER happens to run in, and isoNaiveUTC then re-renders it as UTC, so
// the hour the user reads in the message and the hour sitting in their calendar disagree by the
// server's offset. Nine hours off is not a rounding error, it is a different appointment. No offset →
// no calendar write, and the report says the entry could not be made.
const OFFSET_ISO = /T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$/i;
function offsetAwareStartMs(iso) {
  const value = String(iso || "");
  if (!OFFSET_ISO.test(value)) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

// The readback text is up to 4000 characters of the provider's own page — which, on a confirmation
// screen, is the name, phone number and email that were just typed into the form. lm_care_scan_log is
// append-only, so anything that lands there lands forever: the row keeps the identifiers the provider
// handed back and a boolean for whether a confirmation sentence matched, and never the page itself.
function sanitizeConfirmation(confirmation) {
  if (!confirmation || typeof confirmation !== "object") return null;
  return {
    number: confirmation.number || null,
    booking_id: confirmation.booking_id || null,
    matched_signal: confirmation.matched_signal === true,
  };
}

async function runAftercare({ booking, candidate, candidates, careType, sinceDays, user, deps = {} } = {}) {
  if (!booking || !booking.outcome) return { status: "skipped", reason: "no-booking-outcome" };
  const logError = deps.logError || console.error;
  const booked = booking.outcome === "booked";

  // The calendar write happens BEFORE the message is rendered, because the message CONTAINS a claim
  // about that write. Rendering first and writing after is how 「カレンダーに入れてあります」 ends up
  // in a user's Telegram with nothing in their calendar.
  let calendarEventCreated = false;
  if (booked && deps.calendar && booking.booked_slot) {
    const startMs = offsetAwareStartMs(booking.booked_slot);
    if (startMs !== null) {
      try {
        const created = await deps.calendar.createEvent(user?.uid, {
          summary: candidate?.public_name || "予約",
          start_datetime: isoNaiveUTC(startMs),
          event_duration_hour: 1,
          event_duration_minutes: 0,
          calendar_id: "primary",
          timezone: "UTC",
          location: candidate?.official_url || "",
          description: `Life Manager が予約しました。${booking.confirmation?.number ? `予約番号: ${booking.confirmation.number}` : ""}`.trim(),
        });
        calendarEventCreated = Boolean(created && created.successful);
      } catch (error) {
        calendarEventCreated = false;
        logError(`[care] aftercare-calendar-failed uid=${user?.uid} ${String((error && error.message) || error)}`);
      }
    } else {
      logError(`[care] aftercare-calendar-skipped uid=${user?.uid} reason=slot_timezone_missing slot=${booking.booked_slot}`);
    }
  }

  const message = formatCareBookingReport({
    outcome: booking.outcome,
    careType,
    sinceDays,
    providerName: candidate?.public_name || "",
    usualProvider: candidate?.usual_provider === true,
    slotIso: booking.booked_slot || null,
    reservationUrl: candidate?.reservation_url || booking.reservation_url || "",
    reason: booking.reason || "",
    calendarEventCreated,
    candidates: Array.isArray(candidates) ? candidates : (candidate ? [candidate] : []),
  });

  let telegramMessageId = null;
  let status = "unreachable";
  if (user?.telegram_chat_id && deps.sendMessage) {
    try {
      const response = await deps.sendMessage(deps.telegramToken, user.telegram_chat_id, message);
      const messageId = response && response.result && response.result.message_id;
      if (response && response.ok && messageId !== undefined && messageId !== null) {
        telegramMessageId = messageId;
        status = "reported";
      } else {
        status = "send_failed";
      }
    } catch (error) {
      status = "send_failed";
      logError(`[care] aftercare-send-failed uid=${user?.uid} ${String((error && error.message) || error)}`);
    }
  }

  const record = {
    outcome: booking.outcome,
    provider_id: booking.provider_id || null,
    booked_slot: booking.booked_slot || null,
    confirmation: sanitizeConfirmation(booking.confirmation),
    reason_code: booking.reason_code || null,
    telegram_message_id: telegramMessageId,
    calendar_event_created: calendarEventCreated,
  };
  let recorded = false;
  if (deps.recordBooking) {
    try {
      recorded = Boolean(await deps.recordBooking(record));
    } catch (error) {
      logError(`[care] aftercare-record-failed uid=${user?.uid} ${String((error && error.message) || error)}`);
    }
    if (!recorded) logError(`[care] aftercare-record-failed uid=${user?.uid} outcome=${booking.outcome}`);
  }

  return { status, message, telegramMessageId, calendarEventCreated, recorded, record };
}

module.exports = { runAftercare };
