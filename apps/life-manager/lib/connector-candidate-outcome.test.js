"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  classifyConnectorCandidateOutcome,
  isVerifiedConnectorCandidateOutcome,
} = require("./connector-candidate-outcome.js");

test("write results are normalized into the four candidate attempt outcomes", () => {
  const cases = [
    {
      name: "delivered registration",
      write: { status: "incomplete", outcome: "open_coverage", event_ref: "luma-event://event/registered" },
      want: { classification: "verified_success", retryable: false, suppress_candidate: true },
    },
    {
      name: "provider reports RSVP unavailable before any effect",
      write: {
        status: "incomplete",
        outcome: "application_failed",
        error_code: "LUMA_RSVP_UNAVAILABLE",
        event_ref: "luma-event://event/unavailable",
      },
      want: { classification: "known_no_effect", retryable: false, suppress_candidate: true },
    },
    {
      name: "required private profile answer is unavailable before confirm",
      write: {
        status: "incomplete",
        outcome: "application_failed",
        error_code: "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE",
        event_ref: "luma-event://event/profile-unavailable",
      },
      want: { classification: "known_no_effect", retryable: false, suppress_candidate: true },
    },
    ...[
      "LUMA_CONTROL_UNAVAILABLE",
      "LUMA_FORM_SCHEMA_UNAVAILABLE",
      "LUMA_FORM_PLAN_UNAVAILABLE",
      "LUMA_FORM_FILL_UNAVAILABLE",
      "LUMA_CONFIRM_UNAVAILABLE",
    ].map((errorCode, index) => ({
      name: `${errorCode} is a candidate-local pre-confirm failure`,
      write: {
        status: "incomplete",
        outcome: "application_failed",
        error_code: errorCode,
        event_ref: `luma-event://event/preconfirm-${index}`,
      },
      want: { classification: "known_no_effect", retryable: false, suppress_candidate: true },
    })),
    {
      name: "provider cannot prove whether submit happened",
      write: {
        status: "reconciliation_required",
        outcome: "unknown_external_effect",
        error_code: "LUMA_EFFECT_UNKNOWN",
        event_ref: "luma-event://event/unknown",
      },
      want: { classification: "unknown_effect", retryable: false, suppress_candidate: true },
    },
    {
      name: "registration succeeded but Calendar sync needs recovery",
      write: {
        status: "incomplete",
        outcome: "calendar_sync_failed",
        error_code: "CALENDAR_WRITE_FAILED",
        event_ref: "luma-event://event/recover",
      },
      want: { classification: "recovery_required", retryable: true, suppress_candidate: true },
    },
  ];

  for (const fixture of cases) {
    const actual = classifyConnectorCandidateOutcome(fixture.write);
    assert.equal(isVerifiedConnectorCandidateOutcome(actual), true, fixture.name);
    assert.deepEqual({
      classification: actual.classification,
      retryable: actual.retryable,
      suppress_candidate: actual.suppress_candidate,
    }, fixture.want, fixture.name);
    assert.equal(actual.event_ref, fixture.write.event_ref, fixture.name);
  }
});

test("unknown and malformed write results are rejected instead of guessed", () => {
  assert.throws(
    () => classifyConnectorCandidateOutcome({ status: "incomplete", outcome: "surprise" }),
    /candidate outcome invalid/,
  );
  assert.throws(() => classifyConnectorCandidateOutcome(null), /candidate outcome invalid/);
});
