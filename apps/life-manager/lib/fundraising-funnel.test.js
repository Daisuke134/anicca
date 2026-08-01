"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildFundraisingFunnel, validateFundraisingFunnel } = require("./fundraising-funnel.js");

const SOURCE = `funder-ledger:${"a".repeat(64)}`;
const at = (hour) => `2026-08-01T${String(hour).padStart(2, "0")}:00:00.000Z`;
const event = (eventKind, hour, overrides = {}) => ({
  funder_id: "yc-fall-2026",
  source_id: SOURCE,
  event_kind: eventKind,
  occurred_at: at(hour),
  ...overrides,
});

test("current verified YC source projects only application and confirmation as reached", () => {
  const result = buildFundraisingFunnel({ schema_version: 1, events: [
    event("application", 17), event("confirmation", 17),
  ] });
  assert.deepEqual(result, {
    schema_version: 1,
    summary: {
      application: 1, confirmation: 1, interview: 0,
      offer: 0, rejected: 0, funded: 0,
    },
    applications: [{
      program: "YC Fall 2026",
      current_stage: "confirmation",
      terminal_outcome: null,
      last_event_at: at(17),
      stages: [
        { id: "application", state: "reached", occurred_at: at(17) },
        { id: "confirmation", state: "reached", occurred_at: at(17) },
        { id: "interview", state: "pending", occurred_at: null },
        { id: "decision", state: "pending", outcome: null, occurred_at: null },
        { id: "funded", state: "pending", occurred_at: null },
      ],
    }],
  });
});

test("complete funding path and rejection branch remain distinct and count real observations", () => {
  const second = `funder-ledger:${"b".repeat(64)}`;
  const result = buildFundraisingFunnel({ schema_version: 1, events: [
    event("application", 1), event("confirmation", 2), event("interview", 3),
    event("offer", 4), event("funded", 5),
    event("application", 1, { source_id: second }),
    event("confirmation", 2, { source_id: second }),
    event("rejected", 4, { source_id: second }),
  ] });
  assert.deepEqual(result.summary, {
    application: 2, confirmation: 2, interview: 1,
    offer: 1, rejected: 1, funded: 1,
  });
  assert.equal(result.applications[0].current_stage, "funded");
  assert.equal(result.applications[0].terminal_outcome, "funded");
  assert.equal(result.applications[1].current_stage, "confirmation");
  assert.equal(result.applications[1].terminal_outcome, "rejected");
  assert.deepEqual(result.applications[1].stages[3], {
    id: "decision", state: "reached", outcome: "rejected", occurred_at: at(4),
  });
});

test("a verified empty snapshot is an honest zero funnel", () => {
  assert.deepEqual(buildFundraisingFunnel({ schema_version: 1, events: [] }), {
    schema_version: 1,
    summary: {
      application: 0, confirmation: 0, interview: 0,
      offer: 0, rejected: 0, funded: 0,
    },
    applications: [],
  });
});

test("cross-source, reverse order, impossible terminal states, duplicates, extra fields, and secrets fail closed", () => {
  const invalid = [
    [event("confirmation", 2)],
    [event("application", 2), event("confirmation", 1)],
    [event("application", 1), event("confirmation", 2), event("funded", 3)],
    [event("application", 1), event("confirmation", 2), event("interview", 3), event("offer", 4), event("rejected", 5)],
    [event("application", 1), event("confirmation", 2), event("rejected", 3), event("interview", 4)],
    [event("application", 1), event("application", 2)],
    [event("application", 1, { extra: true })],
    [event("application", 1, { funder_id: "sk_live_secretvalue123" })],
    [event("application", 1, { event_kind: "accepted" })],
    [event("application", 1, { occurred_at: "not-a-date" })],
  ];
  for (const events of invalid) {
    assert.throws(() => buildFundraisingFunnel({ schema_version: 1, events }), /fundraising funnel invalid/);
  }
  assert.throws(() => buildFundraisingFunnel({ schema_version: 1, events: [], extra: true }), /fundraising funnel invalid/);
});

test("closed DTO validator rejects inconsistent stage labels and chronology", () => {
  const valid = buildFundraisingFunnel({ schema_version: 1, events: [
    event("application", 1), event("confirmation", 2), event("interview", 3),
  ] });
  assert.equal(validateFundraisingFunnel(valid), valid);
  for (const mutate of [
    (copy) => { copy.applications[0].current_stage = "application"; },
    (copy) => { copy.applications[0].last_event_at = at(2); },
    (copy) => { copy.applications[0].stages[1].occurred_at = at(4); },
  ]) {
    const copy = structuredClone(valid);
    mutate(copy);
    assert.throws(() => validateFundraisingFunnel(copy), /fundraising funnel invalid/);
  }
});
