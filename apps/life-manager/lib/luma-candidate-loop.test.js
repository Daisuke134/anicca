"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  runLumaCandidateSequence,
} = require("./luma-candidate-loop.js");

const candidates = [
  { event_ref: "luma-event://event/a", canonical_url: "https://luma.com/a", event_date: "2026-08-10" },
  { event_ref: "luma-event://event/b", canonical_url: "https://luma.com/b", event_date: "2026-08-10" },
  { event_ref: "luma-event://event/c", canonical_url: "https://luma.com/c", event_date: "2026-08-10" },
];

test("continues to the next same-day candidate until registration is verified", async () => {
  const calls = [];
  const outcomes = [
    { status: "full" },
    { status: "waitlist" },
    { status: "verified_registered", receipt_ref: "provider-receipt://luma/guest-c" },
  ];
  const result = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async (candidate) => {
      calls.push(candidate.event_ref);
      return outcomes[calls.length - 1];
    },
  });

  assert.equal(result.status, "booked");
  assert.equal(result.candidate.event_ref, candidates[2].event_ref);
  assert.equal(result.receipt_ref, "provider-receipt://luma/guest-c");
  assert.deepEqual(calls, candidates.map(({ event_ref }) => event_ref));
  assert.deepEqual(result.skipped, [
    { event_ref: candidates[0].event_ref, reason: "full" },
    { event_ref: candidates[1].event_ref, reason: "waitlist" },
  ]);
});

test("global login failure triggers recovery instead of burning every candidate", async () => {
  let calls = 0;
  const result = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async () => {
      calls += 1;
      return { status: "login_required" };
    },
  });

  assert.equal(calls, 1);
  assert.deepEqual(result, {
    status: "recovery_required",
    reason: "login_required",
    candidate: candidates[0],
    skipped: [],
  });
});

test("unknown external effect stops for reconciliation before any retry", async () => {
  let calls = 0;
  const result = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async () => {
      calls += 1;
      return { status: "unknown_effect" };
    },
  });

  assert.equal(calls, 1);
  assert.equal(result.status, "reconciliation_required");
  assert.equal(result.candidate.event_ref, candidates[0].event_ref);
});

test("candidate exhaustion explicitly hands the date to the next provider", async () => {
  const result = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async () => ({ status: "not_eligible" }),
  });

  assert.equal(result.status, "next_provider_required");
  assert.equal(result.reason, "luma_candidates_exhausted");
  assert.equal(result.skipped.length, 3);
});

test("known application failure, full, and ineligible all advance until a verified booking", async () => {
  const calls = [];
  const outcomes = [
    { status: "application_failed" },
    { status: "full" },
    { status: "verified_registered", receipt_ref: "provider-receipt://luma/verified-c" },
  ];
  const result = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async (candidate) => {
      calls.push(candidate.event_ref);
      return outcomes[calls.length - 1];
    },
  });
  assert.equal(result.status, "booked");
  assert.equal(result.candidate.event_ref, "luma-event://event/c");
  assert.deepEqual(result.skipped, [
    { event_ref: "luma-event://event/a", reason: "application_failed" },
    { event_ref: "luma-event://event/b", reason: "full" },
  ]);
});

test("refuses to mix another day's candidate into the sequence", async () => {
  let calls = 0;
  await assert.rejects(runLumaCandidateSequence({
    date: "2026-08-10",
    candidates: [candidates[0], { ...candidates[1], event_date: "2026-08-11" }],
    attempt: async () => { calls += 1; return { status: "full" }; },
  }), /date/i);
  assert.equal(calls, 0);
});

test("a known pre-effect adapter failure advances, while an unknown effect never does", async () => {
  let knownCalls = 0;
  const known = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async () => {
      knownCalls += 1;
      if (knownCalls === 1) {
        const error = new Error("form rejected before submit");
        error.unknownEffect = false;
        throw error;
      }
      return { status: "verified_registered", receipt_ref: "provider-receipt://luma/known-next" };
    },
  });
  assert.equal(known.status, "booked");
  assert.equal(knownCalls, 2);
  assert.deepEqual(known.skipped, [
    { event_ref: "luma-event://event/a", reason: "application_failed" },
  ]);

  let unknownCalls = 0;
  const unknown = await runLumaCandidateSequence({
    date: "2026-08-10",
    candidates,
    attempt: async () => {
      unknownCalls += 1;
      const error = new Error("submit connection lost");
      error.unknownEffect = true;
      throw error;
    },
  });
  assert.equal(unknown.status, "reconciliation_required");
  assert.equal(unknownCalls, 1);
});
