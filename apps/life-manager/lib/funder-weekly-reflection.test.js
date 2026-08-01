"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");

const {
  tokyoReflectionWeek,
  latestCompletedTokyoReflectionWeek,
  buildFunderWeeklyReflection,
  isVerifiedFunderWeeklyReflection,
} = require("./funder-weekly-reflection.js");

const sha = (value) => createHash("sha256").update(String(value)).digest("hex");
const NOW = "2026-08-02T12:00:00.000Z"; // Sunday 21:00 JST

function exposure(id, candidateId, occurredAt = "2026-07-28T01:00:00.000Z") {
  return {
    exposure_id: id,
    candidate_id: candidateId,
    exposure_kind: "outreach",
    occurred_at: occurredAt,
    subject_sha256: sha(`${id}:subject`),
    body_sha256: sha(`${id}:body`),
  };
}

function outcome(id, exposureId, candidateId, status, observedAt) {
  return {
    result_id: id,
    exposure_id: exposureId,
    candidate_id: candidateId,
    status,
    observed_at: observedAt,
  };
}

function base(overrides = {}) {
  return {
    tenantId: "dais-local",
    reflectedAt: NOW,
    exposures: [
      exposure("funder-outreach:a", "alpha"),
      exposure("funder-outreach:b", "beta"),
    ],
    results: [],
    candidates: ["alpha", "beta"],
    ...overrides,
  };
}

function judgment(overrides = {}) {
  return {
    kind: "agent_judgment",
    decision: "change",
    summary: "Meeting evidence favors beta's concrete workflow thesis.",
    rationale: "Move beta first and lead with the verified workflow outcome.",
    used_result_ids: ["funder-result:meeting"],
    ranked_candidate_ids: ["beta", "alpha"],
    pitch_directives: [
      {
        candidate_id: "beta",
        directive: "Lead with the verified autonomous workflow and ask for a 15-minute fit call.",
        outcome_result_ids: ["funder-result:meeting"],
      },
      {
        candidate_id: "alpha",
        directive: "Keep the company facts, but foreground the concrete workflow before the product breadth.",
        outcome_result_ids: ["funder-result:meeting"],
      },
    ],
    ...overrides,
  };
}

test("Tokyo reflection week is Monday-inclusive and Sunday-20:15-exclusive", () => {
  assert.deepEqual(tokyoReflectionWeek(NOW), {
    week_key: "2026-07-27",
    week_start: "2026-07-26T15:00:00.000Z",
    week_end: "2026-08-02T11:15:00.000Z",
  });
});

test("after downtime, Monday still points to the just-completed Sunday cutoff", () => {
  assert.deepEqual(latestCompletedTokyoReflectionWeek("2026-08-03T01:00:00.000Z"), {
    week_key: "2026-07-27",
    week_start: "2026-07-26T15:00:00.000Z",
    week_end: "2026-08-02T11:15:00.000Z",
  });
});

test("zero learnable outcomes creates a verified truthful hold without agent invention", () => {
  const value = buildFunderWeeklyReflection(base({
    results: [outcome(
      "funder-result:confirmation",
      "funder-outreach:a",
      "alpha",
      "confirmed",
      "2026-07-29T01:00:00.000Z",
    )],
  }));
  assert.equal(value.decision, "hold");
  assert.equal(value.reason, "insufficient_outcomes");
  assert.deepEqual(value.outcome_result_ids, []);
  assert.deepEqual(value.ranked_candidate_ids, []);
  assert.deepEqual(value.pitch_directives, []);
  assert.equal(isVerifiedFunderWeeklyReflection(value), true);
});

test("verified meeting outcome can revise the complete next ranking and pitch directives", () => {
  const value = buildFunderWeeklyReflection(base({
    results: [outcome(
      "funder-result:meeting",
      "funder-outreach:b",
      "beta",
      "meeting_requested",
      "2026-07-31T02:00:00.000Z",
    )],
    judgment: judgment(),
  }));
  assert.equal(value.decision, "change");
  assert.deepEqual(value.outcome_result_ids, ["funder-result:meeting"]);
  assert.deepEqual(value.ranked_candidate_ids, ["beta", "alpha"]);
  assert.equal(value.pitch_directives[0].candidate_id, "beta");
  assert.equal(value.pitch_directives[0].directive_sha256, sha(value.pitch_directives[0].directive));
  assert.match(value.reflection_id, /^funder-weekly-reflection:[0-9a-f]{64}$/);
  assert.equal(isVerifiedFunderWeeklyReflection(value), true);
  assert.equal(isVerifiedFunderWeeklyReflection(JSON.parse(JSON.stringify(value))), false);
});

test("an unreflected late-committed learnable result is accepted in the next week", () => {
  const value = buildFunderWeeklyReflection({
    ...base(),
    reflectedAt: "2026-08-09T12:00:00.000Z",
    week: tokyoReflectionWeek("2026-08-05T00:00:00.000Z"),
    results: [outcome(
      "funder-result:late-meeting", "funder-outreach:b", "beta",
      "meeting_requested", "2026-08-01T02:00:00.000Z",
    )],
    judgment: judgment({ used_result_ids: ["funder-result:late-meeting"], pitch_directives: [
      { ...judgment().pitch_directives[0], outcome_result_ids: ["funder-result:late-meeting"] },
      { ...judgment().pitch_directives[1], outcome_result_ids: ["funder-result:late-meeting"] },
    ] }),
  });
  assert.deepEqual(value.outcome_result_ids, ["funder-result:late-meeting"]);
});

test("reply, rejection, meeting, offer, and funded are learnable; confirmation is not", () => {
  for (const status of ["reply_received", "rejected", "meeting_requested", "offer_received", "funded"]) {
    const resultId = `funder-result:${status}`;
    const value = buildFunderWeeklyReflection(base({
      results: [outcome(resultId, "funder-outreach:a", "alpha", status, "2026-07-30T01:00:00.000Z")],
      judgment: judgment({
        used_result_ids: [resultId],
        pitch_directives: judgment().pitch_directives.map((item) => ({
          ...item,
          outcome_result_ids: [resultId],
        })),
      }),
    }));
    assert.equal(value.outcome_result_ids[0], resultId);
  }
});

test("look-ahead, unknown lineage, changed target, and changed exposure hashes fail closed", () => {
  const cases = [
    outcome("funder-result:future", "funder-outreach:a", "alpha", "rejected", "2026-08-02T11:15:00.000Z"),
    outcome("funder-result:missing", "funder-outreach:missing", "alpha", "rejected", "2026-07-30T01:00:00.000Z"),
    outcome("funder-result:target", "funder-outreach:a", "beta", "rejected", "2026-07-30T01:00:00.000Z"),
  ];
  for (const result of cases) {
    assert.throws(() => buildFunderWeeklyReflection(base({ results: [result], judgment: judgment() })), /invalid/);
  }
  const changed = base();
  changed.exposures[0].body_sha256 = sha("tampered");
  changed.exposures.push({ ...changed.exposures[0] });
  assert.throws(() => buildFunderWeeklyReflection(changed), /invalid/);
});

test("agent must cite the exact complete outcome set and a complete candidate permutation", () => {
  const input = base({
    results: [
      outcome("funder-result:meeting", "funder-outreach:b", "beta", "meeting_requested", "2026-07-31T02:00:00.000Z"),
      outcome("funder-result:reject", "funder-outreach:a", "alpha", "rejected", "2026-08-01T02:00:00.000Z"),
    ],
  });
  const invalid = [
    judgment(),
    judgment({ used_result_ids: ["funder-result:meeting", "funder-result:reject"], ranked_candidate_ids: ["beta", "beta"] }),
    judgment({ used_result_ids: ["funder-result:meeting", "funder-result:reject"], ranked_candidate_ids: ["beta"] }),
    judgment({ used_result_ids: ["funder-result:meeting", "funder-result:reject"], pitch_directives: [judgment().pitch_directives[0]] }),
    judgment({ used_result_ids: ["funder-result:meeting", "funder-result:reject"], pitch_directives: judgment().pitch_directives.map((item) => ({ ...item, outcome_result_ids: ["funder-result:fake"] })) }),
  ];
  for (const candidate of invalid) {
    assert.throws(() => buildFunderWeeklyReflection({ ...input, judgment: candidate }), /invalid/);
  }
});

test("pitch directives close at one line, 24 words, and 240 characters", () => {
  const input = base({
    results: [outcome(
      "funder-result:meeting", "funder-outreach:b", "beta",
      "meeting_requested", "2026-07-31T02:00:00.000Z",
    )],
  });
  for (const directive of [
    Array.from({ length: 25 }, (_, index) => `word${index}`).join(" "),
    "first line\nsecond line",
    "x".repeat(241),
  ]) {
    const changed = judgment();
    changed.pitch_directives[0] = { ...changed.pitch_directives[0], directive };
    assert.throws(() => buildFunderWeeklyReflection({ ...input, judgment: changed }), /invalid/);
  }
});

test("agent may explicitly hold after outcomes but cannot smuggle ranking or pitch changes", () => {
  const value = buildFunderWeeklyReflection(base({
    results: [outcome("funder-result:meeting", "funder-outreach:b", "beta", "meeting_requested", "2026-07-31T02:00:00.000Z")],
    judgment: judgment({ decision: "hold", ranked_candidate_ids: [], pitch_directives: [] }),
  }));
  assert.equal(value.decision, "hold");
  assert.equal(value.reason, "agent_hold");
  assert.throws(() => buildFunderWeeklyReflection(base({
    results: [outcome("funder-result:meeting", "funder-outreach:b", "beta", "meeting_requested", "2026-07-31T02:00:00.000Z")],
    judgment: judgment({ decision: "hold" }),
  })), /invalid/);
});
