"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const {
  validateRegistry,
  canonicalJson,
  sha256Canonical,
  matchesLabel,
  classifyLabel,
} = require("./cfo-registry.js");

function validFixture() {
  return {
    schema_version: 1,
    registry_id: "life_manager_cfo_financial_units",
    relevant_runtime_prefixes: ["ai.anicca.writer-", "ai.anicca.cfo-"],
    financial_units: [{
      financial_unit_id: "writer_agent", unit_kind: "business", display_order: 1,
      display_name: { en: "Writer Agent", ja: "Writer Agent" }, owner_ref: "human:dais",
      cost_center_refs: [], lifecycle: "active", runtime_matchers: ["ai.anicca.writer-*"],
      revenue_channel_ids: ["publisher_writer"], ledger_source_ids: ["writer_receipts"],
      evidence_refs: ["docs/writer-agent/WRITER-AGENT-SSOT.md"],
    }],
    runtime_exclusions: [{
      exclusion_id: "cfo_controller", runtime_matchers: ["ai.anicca.cfo-*"],
      classification: "controller", cost_treatment: "shared_overhead",
      evidence_refs: ["docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md"],
    }],
  };
}

function clone(value) {
  return structuredClone(value);
}

function invalidMutations() {
  return [
    (value) => {
      const next = clone(value);
      next.unknown_root_key = true;
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].unknown_unit_key = true;
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units.push(clone(next.financial_units[0]));
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].revenue_channel_ids = ["publisher_writer", "publisher_writer"];
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].unit_kind = "other";
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].lifecycle = "unknown";
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].evidence_refs = [];
      return next;
    },
    (value) => {
      const next = clone(value);
      next.monthly_revenue = 0;
      return next;
    },
    (value) => {
      const next = clone(value);
      next.api_secret = "not-a-secret";
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].owner_ref = "/Users/name/state";
      return next;
    },
    (value) => {
      const next = clone(value);
      next.financial_units[0].runtime_matchers = ["ai.anicca.*.writer-report"];
      return next;
    },
  ];
}

test("valid registry is frozen and exact/terminal-star labels classify once", () => {
  const registry = validateRegistry(validFixture());
  assert.equal(Object.isFrozen(registry), true);
  assert.equal(Object.isFrozen(registry.financial_units), true);
  assert.equal(Object.isFrozen(registry.financial_units[0]), true);
  assert.deepEqual(classifyLabel(registry, "ai.anicca.writer-report"), {
    kind: "financial_unit", targetIds: ["writer_agent"],
  });
  assert.deepEqual(classifyLabel(registry, "ai.anicca.cfo-controller"), {
    kind: "exclusion", targetIds: ["cfo_controller"],
  });
  assert.deepEqual(classifyLabel(registry, "ai.anicca.other"), {
    kind: "unmapped", targetIds: [],
  });
  assert.equal(matchesLabel("ai.anicca.writer-*", "ai.anicca.writer-report"), true);
  assert.equal(matchesLabel("ai.anicca.writer-report", "ai.anicca.writer-report"), true);
  assert.equal(matchesLabel("ai.*.writer-*", "ai.anicca.writer-report"), false);
  assert.equal(matchesLabel("ai.anicca.writer-*", "ai.anicca.writer-report-extra"), true);
  assert.equal(matchesLabel("ai.anicca.writer-*", "ai.anicca.writer"), false);
});

test("duplicates, unknown keys, money, secret-like keys, unsafe paths, and overlap fail", () => {
  for (const mutate of invalidMutations()) {
    assert.throws(() => validateRegistry(mutate(validFixture())), /^Error: cfo_registry_invalid:/);
  }
});

test("canonical hash ignores object insertion order but preserves array order", () => {
  assert.equal(sha256Canonical({ b: 2, a: 1 }), sha256Canonical({ a: 1, b: 2 }));
  assert.equal(canonicalJson({ b: 2, a: 1 }), '{"a":1,"b":2}');
  assert.notEqual(sha256Canonical({ a: [1, 2] }), sha256Canonical({ a: [2, 1] }));
  assert.match(sha256Canonical({ a: 1 }), /^[0-9a-f]{64}$/);
});
