"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { resolveCareBookingOutcome } = require("./care-booking");

const fixed = {
  selectedProviderId: "otakibashi-sora",
  attemptedProviderId: "otakibashi-sora",
  channel: "web",
  runtime: "cloud",
};

test("confirmed provider readback closes a booking without exposing patient data", () => {
  assert.deepEqual(resolveCareBookingOutcome({
    ...fixed,
    providerReadback: { confirmed: true, bookingId: "booking-public-id" },
  }), {
    schema_version: 1,
    status: "booked",
    provider_id: "otakibashi-sora",
    channel: "web",
    booking_id: "booking-public-id",
    blocker: null,
    telegram_message_id: null,
  });
});

test("SMS identity gate produces an honest Telegram outcome and preserves provider", () => {
  assert.deepEqual(resolveCareBookingOutcome({
    ...fixed,
    providerReadback: { confirmed: false },
    blocker: "patient_sms_verification_required",
    telegramMessageId: 3393,
  }), {
    schema_version: 1,
    status: "honest_failure_reported",
    provider_id: "otakibashi-sora",
    channel: "web",
    booking_id: null,
    blocker: "patient_sms_verification_required",
    telegram_message_id: 3393,
  });
});

test("provider switch, phone, local runtime, and unproved success fail closed", () => {
  assert.throws(() => resolveCareBookingOutcome({
    ...fixed,
    attemptedProviderId: "different-provider",
    blocker: "patient_sms_verification_required",
    telegramMessageId: 1,
  }), /provider mutation/);
  assert.throws(() => resolveCareBookingOutcome({
    ...fixed,
    channel: "phone",
    blocker: "patient_sms_verification_required",
    telegramMessageId: 1,
  }), /phone/);
  assert.throws(() => resolveCareBookingOutcome({
    ...fixed,
    runtime: "local",
    blocker: "patient_sms_verification_required",
    telegramMessageId: 1,
  }), /local runtime/);
  assert.throws(() => resolveCareBookingOutcome({
    ...fixed,
    providerReadback: { confirmed: true },
  }), /booking readback/);
});

test("provider communication requires the exact secretary disclosure", () => {
  assert.throws(() => resolveCareBookingOutcome({
    ...fixed,
    providerMessageSent: true,
    providerDisclosure: "AI assistant",
    blocker: "provider_reply_required",
    telegramMessageId: 1,
  }), /disclosure/);
  assert.equal(resolveCareBookingOutcome({
    ...fixed,
    providerMessageSent: true,
    providerDisclosure: "Life Manager (AI secretary, acting for <user>)",
    blocker: "provider_reply_required",
    telegramMessageId: 1,
  }).status, "honest_failure_reported");
});
