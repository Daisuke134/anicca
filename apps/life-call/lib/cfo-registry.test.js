"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

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

test("wildcard-only matcher is accepted consistently by the public and registry contracts", () => {
  assert.equal(matchesLabel("*", "any.launchd.label"), true);
  const fixture = validFixture();
  fixture.financial_units[0].runtime_matchers = ["*"];
  const registry = validateRegistry(fixture);
  assert.deepEqual(classifyLabel(registry, "any.launchd.label"), {
    kind: "financial_unit", targetIds: ["writer_agent"],
  });
});

test("class instances and custom prototypes are rejected before cloning", () => {
  class RegistryLike {}
  const root = Object.assign(new RegistryLike(), validFixture());
  assert.throws(() => validateRegistry(root), /^Error: cfo_registry_invalid:/);

  const unit = Object.assign(Object.create({ custom: true }), validFixture().financial_units[0]);
  const unitFixture = validFixture();
  unitFixture.financial_units[0] = unit;
  assert.throws(() => validateRegistry(unitFixture), /^Error: cfo_registry_invalid:/);

  const displayName = Object.assign(Object.create({ custom: true }), { en: "Writer Agent", ja: "Writer Agent" });
  const displayNameFixture = validFixture();
  displayNameFixture.financial_units[0].display_name = displayName;
  assert.throws(() => validateRegistry(displayNameFixture), /^Error: cfo_registry_invalid:/);
});

test("typed owner and cost-center references preserve their namespaces", () => {
  const fixture = validFixture();
  fixture.financial_units[0].cost_center_refs = ["agent:franklin1", "agent:franklin2"];
  const registry = validateRegistry(fixture);
  assert.equal(registry.financial_units[0].owner_ref, "human:dais");
  assert.deepEqual(registry.financial_units[0].cost_center_refs, ["agent:franklin1", "agent:franklin2"]);
});

test("typed owner and cost-center references reject untyped or wrong namespaces", () => {
  const mutations = [
    (fixture) => { fixture.financial_units[0].owner_ref = "dais"; },
    (fixture) => { fixture.financial_units[0].owner_ref = "agent:dais"; },
    (fixture) => { fixture.financial_units[0].cost_center_refs = ["franklin1"]; },
    (fixture) => { fixture.financial_units[0].cost_center_refs = ["human:franklin1"]; },
  ];
  for (const mutate of mutations) {
    const fixture = validFixture();
    mutate(fixture);
    assert.throws(() => validateRegistry(fixture), /^Error: cfo_registry_invalid:/);
  }
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

test("canonical registry exposes exactly seven ordered financial units", () => {
  const raw = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/cfo-financial-units.json"), "utf8"));
  const registry = validateRegistry(raw);
  assert.deepEqual(registry.financial_units.map((unit) => unit.financial_unit_id), [
    "life_manager_saas", "anicca_ios", "writer_agent", "affiliate_agent",
    "gig_work", "x402_services", "job_income",
  ]);
  assert.equal(registry.financial_units.at(-1).unit_kind, "personal_income");
  assert.ok(registry.financial_units.slice(0, -1).every((unit) => unit.unit_kind === "business"));
  assert.deepEqual(registry.financial_units.map((unit) => unit.display_order), [1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.owner_ref), Array(7).fill("human:dais"));
  assert.deepEqual(registry.financial_units.map((unit) => unit.display_name), [
    { en: "Life Manager", ja: "ライフマネージャー" },
    { en: "Anicca iOS", ja: "アニッチャ iOS" },
    { en: "Writer Agent", ja: "ライターエージェント" },
    { en: "Affiliate Agent", ja: "アフィリエイトエージェント" },
    { en: "Gig Work", ja: "ギグワーク" },
    { en: "x402 Services", ja: "x402サービス" },
    { en: "Employment Income", ja: "給与所得" },
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.lifecycle), [
    "active", "active", "active", "building", "active", "active", "active",
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.runtime_matchers), [
    ["ai.anicca.life-manager-*"], [], ["ai.anicca.writer-*"], ["ai.anicca.affiliate-*"],
    ["ai.anicca.hf-gig-*", "ai.anicca.gig-outcome-watch"], ["ai.anicca.x402-*"],
    ["ai.anicca.job-search-*"],
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.revenue_channel_ids), [
    ["stripe_life_manager", "taskmarket_life_manager", "ugig_life_manager"],
    ["apple_app_store_anicca"], ["note_writer", "substack_writer", "publisher_writer"],
    ["amazon_associates", "rakuten_affiliate", "affiliate_networks"],
    ["gig_marketplaces", "direct_gig_clients"], ["x402_onchain"], ["payroll_bank"],
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.ledger_source_ids), [
    ["lm_financial_ledger"], ["revenuecat_anicca_ios"], ["writer_receipts"],
    ["affiliate_commission_receipts"], ["gig_payment_receipts"],
    ["x402_settlement_receipts"], ["payroll_bank_receipts"],
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.cost_center_refs), [
    [], [], [], [], [], ["agent:franklin1", "agent:franklin2"], [],
  ]);
  assert.deepEqual(registry.financial_units.map((unit) => unit.evidence_refs), [
    ["docs/superpowers/specs/2026-06-21-life-manager-LAUNCH-ORDER.md"],
    ["AGENTS.md"], ["docs/writer-agent/WRITER-AGENT-SSOT.md"],
    ["docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md"],
    ["docs/loop-engineering/26-gig-loop-asis-tobe-plan.md"],
    ["apps/x402-agents/package.json"], ["launchd:ai.anicca.job-search-*"],
  ]);
  assert.deepEqual(registry.relevant_runtime_prefixes, [
    "ai.anicca.life-manager-", "ai.anicca.writer-", "ai.anicca.affiliate-",
    "ai.anicca.hf-gig-", "ai.anicca.gig-outcome-watch", "ai.anicca.x402-",
    "ai.anicca.job-search-", "ai.anicca.cfo-", "ai.anicca.fleet-",
    "ai.anicca.franklin", "ai.anicca.self-fix-", "ai.anicca.connector-healer-",
  ]);
  assert.deepEqual(registry.runtime_exclusions, [
    {
      exclusion_id: "cfo_controller", runtime_matchers: ["ai.anicca.cfo-*"],
      classification: "controller", cost_treatment: "shared_overhead",
      evidence_refs: ["docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md"],
    },
    {
      exclusion_id: "fleet_observer", runtime_matchers: ["ai.anicca.fleet-*"],
      classification: "observer", cost_treatment: "shared_overhead",
      evidence_refs: ["docs/superpowers/specs/2026-08-04-fleet-and-remote-stability-design.md"],
    },
    {
      exclusion_id: "repair_infrastructure",
      runtime_matchers: ["ai.anicca.self-fix-*", "ai.anicca.connector-healer-*"],
      classification: "repair_infrastructure", cost_treatment: "shared_overhead",
      evidence_refs: ["docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md"],
    },
    {
      exclusion_id: "franklin_cost_centres",
      runtime_matchers: ["ai.anicca.franklin-loop", "ai.anicca.franklin2-loop"],
      classification: "agent_cost_centre", cost_treatment: "x402_services",
      evidence_refs: ["docs/superpowers/specs/2026-08-08-life-manager-cfo-m0-business-registry-design.md"],
    },
  ]);
});

test("canonical runtime namespaces classify financial units and exclusions", () => {
  const raw = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/cfo-financial-units.json"), "utf8"));
  const registry = validateRegistry(raw);
  const cases = [
    ["ai.anicca.life-manager-worker", { kind: "financial_unit", targetIds: ["life_manager_saas"] }],
    ["ai.anicca.writer-worker", { kind: "financial_unit", targetIds: ["writer_agent"] }],
    ["ai.anicca.affiliate-worker", { kind: "financial_unit", targetIds: ["affiliate_agent"] }],
    ["ai.anicca.hf-gig-worker", { kind: "financial_unit", targetIds: ["gig_work"] }],
    ["ai.anicca.gig-outcome-watch", { kind: "financial_unit", targetIds: ["gig_work"] }],
    ["ai.anicca.x402-worker", { kind: "financial_unit", targetIds: ["x402_services"] }],
    ["ai.anicca.job-search-worker", { kind: "financial_unit", targetIds: ["job_income"] }],
    ["ai.anicca.cfo-controller", { kind: "exclusion", targetIds: ["cfo_controller"] }],
    ["ai.anicca.fleet-observer", { kind: "exclusion", targetIds: ["fleet_observer"] }],
    ["ai.anicca.self-fix-repair", { kind: "exclusion", targetIds: ["repair_infrastructure"] }],
    ["ai.anicca.connector-healer-repair", { kind: "exclusion", targetIds: ["repair_infrastructure"] }],
    ["ai.anicca.franklin-loop", { kind: "exclusion", targetIds: ["franklin_cost_centres"] }],
    ["ai.anicca.franklin2-loop", { kind: "exclusion", targetIds: ["franklin_cost_centres"] }],
    ["ai.anicca.unregistered", { kind: "unmapped", targetIds: [] }],
  ];
  for (const [label, expected] of cases) assert.deepEqual(classifyLabel(registry, label), expected, label);
});
