"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  isVerifiedLumaCandidateSequence,
  runLumaCandidateSequence,
} = require("./luma-candidate-loop.js");

const candidates = [
  { event_ref: "luma-event://event/a", canonical_url: "https://luma.com/a" },
  { event_ref: "luma-event://event/b", canonical_url: "https://luma.com/b" },
  { event_ref: "luma-event://event/c", canonical_url: "https://luma.com/c" },
];

test("continues to the next same-day candidate until registration is verified", async () => {
  const calls = [];
  const outcomes = [
    { status: "full" },
    { status: "waitlist" },
    { status: "verified_registered", receipt_ref: "provider-receipt://luma/guest-c" },
  ];
  const result = await runLumaCandidateSequence({
    candidates,
    attempt: async (candidate) => {
      calls.push(candidate.event_ref);
      return outcomes[calls.length - 1];
    },
  });

  assert.equal(result.status, "booked");
  assert.equal(isVerifiedLumaCandidateSequence(result), true);
  assert.equal(isVerifiedLumaCandidateSequence(structuredClone(result)), false);
  assert.equal(result.candidate.event_ref, candidates[2].event_ref);
  assert.equal(result.receipt_ref, "provider-receipt://luma/guest-c");
  assert.deepEqual(calls, candidates.map(({ event_ref }) => event_ref));
  assert.deepEqual(result.skipped, [
    { event_ref: candidates[0].event_ref, reason: "full" },
    { event_ref: candidates[1].event_ref, reason: "waitlist" },
  ]);
});

test("login failure cannot stop the sequence before every candidate and provider handoff", async () => {
  let calls = 0;
  const result = await runLumaCandidateSequence({
    candidates,
    attempt: async () => {
      calls += 1;
      return { status: "login_required" };
    },
  });

  assert.equal(calls, 3);
  assert.deepEqual(result, {
    status: "next_provider_required",
    reason: "luma_candidates_exhausted",
    skipped: candidates.map((candidate) => ({ event_ref: candidate.event_ref, reason: "login_required" })),
  });
});

test("unknown external effect quarantines each candidate without stopping provider handoff", async () => {
  let calls = 0;
  const result = await runLumaCandidateSequence({
    candidates,
    attempt: async () => {
      calls += 1;
      return { status: "unknown_effect" };
    },
  });

  assert.equal(calls, 3);
  assert.equal(result.status, "next_provider_required");
  assert.deepEqual(result.skipped, candidates.map((candidate) => ({
    event_ref: candidate.event_ref,
    reason: "unknown_effect",
  })));
});

test("candidate exhaustion explicitly hands the date to the next provider", async () => {
  const result = await runLumaCandidateSequence({
    candidates,
    attempt: async () => ({ status: "not_eligible" }),
  });

  assert.equal(result.status, "next_provider_required");
  assert.equal(result.reason, "luma_candidates_exhausted");
  assert.equal(result.skipped.length, 3);
});
