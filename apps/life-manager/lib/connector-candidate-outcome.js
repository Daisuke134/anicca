"use strict";

const EVENT_REF = /^(?:luma-event:\/\/event\/[A-Za-z0-9_-]+|connpass-event:\/\/event\/[1-9][0-9]*)$/;
const KNOWN_NO_EFFECT_CODES = new Set([
  "LUMA_CONFIRM_UNAVAILABLE",
  "LUMA_CONTROL_UNAVAILABLE",
  "LUMA_FORM_FILL_UNAVAILABLE",
  "LUMA_FORM_INPUT_REQUIRED",
  "LUMA_FORM_PLAN_UNAVAILABLE",
  "LUMA_FORM_SCHEMA_UNAVAILABLE",
  "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
  "LUMA_RSVP_UNAVAILABLE",
  "CONNPASS_CONTROL_UNAVAILABLE",
  "CONNPASS_LOGIN_REQUIRED",
  "CONNPASS_REGISTRATION_UNAVAILABLE",
  "CONNPASS_RSVP_UNAVAILABLE",
]);
const VERIFIED_SUCCESS_OUTCOMES = new Set([
  "open_coverage",
  "verified_delivery",
]);
const RECOVERY_OUTCOMES = new Set([
  "calendar_sync_failed",
  "coverage_rebuild_failed",
  "registration_evidence_failed",
  "telegram_delivery_failed",
  "telegram_evidence_failed",
  "ticket_evidence_failed",
  "ticket_telegram_failed",
  "telegram_message_build_failed",
]);
const VERIFIED = new WeakSet();

function invalid() {
  throw new Error("Connector candidate outcome invalid");
}

function verified(value) {
  const result = Object.freeze(value);
  VERIFIED.add(result);
  return result;
}

function classifyConnectorCandidateOutcome(write) {
  if (!write || typeof write !== "object" || Array.isArray(write)) invalid();
  const status = String(write.status || "").trim();
  const outcome = String(write.outcome || "").trim();
  const errorCode = String(write.error_code || "").trim();
  const eventRef = String(write.event_ref || "").trim();
  if (!EVENT_REF.test(eventRef)) invalid();

  if (
    ["complete", "incomplete"].includes(status)
    && VERIFIED_SUCCESS_OUTCOMES.has(outcome)
  ) {
    return verified({
      classification: "verified_success",
      event_ref: eventRef,
      retryable: false,
      suppress_candidate: true,
    });
  }
  if (
    status === "incomplete"
    && outcome === "application_failed"
    && KNOWN_NO_EFFECT_CODES.has(errorCode)
  ) {
    return verified({
      classification: "known_no_effect",
      event_ref: eventRef,
      error_code: errorCode,
      retryable: false,
      suppress_candidate: true,
    });
  }
  if (status === "reconciliation_required" && outcome === "unknown_external_effect") {
    return verified({
      classification: "unknown_effect",
      event_ref: eventRef,
      error_code: errorCode || "CONNECTOR_EFFECT_UNKNOWN",
      retryable: false,
      suppress_candidate: true,
    });
  }
  if (status === "incomplete" && RECOVERY_OUTCOMES.has(outcome)) {
    return verified({
      classification: "recovery_required",
      event_ref: eventRef,
      error_code: errorCode || `${outcome.toUpperCase()}_FAILED`,
      retryable: true,
      suppress_candidate: true,
    });
  }
  invalid();
}

function isVerifiedConnectorCandidateOutcome(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  classifyConnectorCandidateOutcome,
  isVerifiedConnectorCandidateOutcome,
};
