"use strict";

const DISCLOSURE = "Life Manager (AI secretary, acting for <user>)";
const ALLOWED_CHANNELS = new Set(["web", "email"]);
const ALLOWED_BLOCKERS = new Set([
  "patient_sms_verification_required",
  "patient_oauth_required",
  "captcha_required",
  "provider_reply_required",
  "no_available_slot",
]);

function resolveCareBookingOutcome(input) {
  if (!input?.selectedProviderId || input.attemptedProviderId !== input.selectedProviderId) {
    throw new Error("provider mutation is forbidden");
  }
  if (input.channel === "phone" || !ALLOWED_CHANNELS.has(input.channel)) {
    throw new Error("phone and unknown booking channels are forbidden");
  }
  if (input.runtime === "local") {
    throw new Error("local runtime cannot be the recurring booking executor");
  }
  if (input.providerMessageSent === true && input.providerDisclosure !== DISCLOSURE) {
    throw new Error("exact AI secretary disclosure is required");
  }

  const confirmed = input.providerReadback?.confirmed === true;
  if (confirmed) {
    if (!input.providerReadback.bookingId) {
      throw new Error("booking readback id is required");
    }
    return {
      schema_version: 1,
      status: "booked",
      provider_id: input.selectedProviderId,
      channel: input.channel,
      booking_id: input.providerReadback.bookingId,
      blocker: null,
      telegram_message_id: null,
    };
  }

  if (!ALLOWED_BLOCKERS.has(input.blocker) || !Number.isInteger(input.telegramMessageId)) {
    throw new Error("honest failure requires a closed blocker and real Telegram message id");
  }
  return {
    schema_version: 1,
    status: "honest_failure_reported",
    provider_id: input.selectedProviderId,
    channel: input.channel,
    booking_id: null,
    blocker: input.blocker,
    telegram_message_id: input.telegramMessageId,
  };
}

module.exports = { DISCLOSURE, resolveCareBookingOutcome };
