"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { validateRegistry, sha256Canonical } = require("./cfo-registry.js");
const {
  normalizeLaunchctlList,
  collectSourceObservations,
  buildInventory,
  observationHash,
} = require("./cfo-inventory.js");

const canonicalRegistry = validateRegistry(JSON.parse(fs.readFileSync(
  path.join(__dirname, "../config/cfo-financial-units.json"),
  "utf8",
)));

function makeInput(labels, registry = canonicalRegistry, overrides = {}) {
  return {
    registry,
    runtimeObservations: labels.map((label) => ({
      label,
      state: "unknown",
      last_exit_code: null,
    })),
    sourceObservations: [],
    generatedAt: "2026-08-08T00:00:00.000Z",
    inventoryId: "00000000-0000-4000-8000-000000000001",
    ...overrides,
  };
}

function registryWithSecondWriterMatcher() {
  const raw = structuredClone(canonicalRegistry);
  raw.runtime_exclusions.push({
    exclusion_id: "synthetic_writer_overlap",
    runtime_matchers: ["ai.anicca.writer-report"],
    classification: "controller",
    cost_treatment: "shared_overhead",
    evidence_refs: ["docs/superpowers/specs/2026-08-08-life-manager-cfo-m0-business-registry-design.md"],
  });
  return validateRegistry(raw);
}

test("inventory maps known labels and is deterministic across input order", () => {
  const first = buildInventory(makeInput(["ai.anicca.writer-report", "ai.anicca.x402-monitor"]));
  const second = buildInventory(makeInput(["ai.anicca.x402-monitor", "ai.anicca.writer-report"]));
  assert.equal(first.observation_hash, second.observation_hash);
  assert.equal(first.result, "pass");
  assert.deepEqual(first.runtime_observations, [
    {
      label: "ai.anicca.writer-report", state: "unknown", last_exit_code: null,
      classification: "financial_unit", target_ids: ["writer_agent"],
    },
    {
      label: "ai.anicca.x402-monitor", state: "unknown", last_exit_code: null,
      classification: "financial_unit", target_ids: ["x402_services"],
    },
  ]);
  assert.deepEqual(first.financial_units.find((unit) => unit.financial_unit_id === "writer_agent"), {
    financial_unit_id: "writer_agent", unit_kind: "business", display_order: 3,
    display_name: { en: "Writer Agent", ja: "ライターエージェント" }, lifecycle: "active",
    runtime_labels: ["ai.anicca.writer-report"],
    source_evidence_refs: [], evidence_status: "observed",
  });
});

test("unmapped relevant and ambiguous labels fail closed", () => {
  const unmapped = buildInventory(makeInput(["ai.anicca.franklin3-loop"]));
  const ambiguous = buildInventory(makeInput(
    ["ai.anicca.writer-report"],
    registryWithSecondWriterMatcher(),
  ));
  assert.deepEqual(unmapped.unmapped_relevant_labels, ["ai.anicca.franklin3-loop"]);
  assert.deepEqual(ambiguous.ambiguous_labels.map((item) => item.label), ["ai.anicca.writer-report"]);
  assert.equal(unmapped.result, "fail");
  assert.equal(ambiguous.result, "fail");
  assert.equal(ambiguous.runtime_observations[0].classification, "ambiguous");
});

test("unknown ai.anicca money runtime fails closed under the complete census root", () => {
  const inventory = buildInventory(makeInput(["ai.anicca.unknown-money-loop"]));
  assert.deepEqual(inventory.unmapped_relevant_labels, ["ai.anicca.unknown-money-loop"]);
  assert.equal(inventory.runtime_observations[0].classification, "unmapped");
  assert.equal(inventory.result, "fail");
});

test("irrelevant labels are ignored and missing-runtime units stay unverified", () => {
  const inventory = buildInventory(makeInput(["completely.irrelevant", "com.example.unregistered"]));
  assert.deepEqual(inventory.runtime_observations, []);
  assert.deepEqual(inventory.unmapped_relevant_labels, []);
  assert.equal(inventory.result, "pass");
  assert.ok(inventory.financial_units.every((unit) => unit.evidence_status === "unverified"));
  assert.ok(inventory.financial_units.every((unit) => unit.runtime_labels.length === 0));
});

test("exit codes are observations and do not become financial health", () => {
  const inventory = buildInventory(makeInput([], canonicalRegistry, {
    runtimeObservations: [
      { label: "ai.anicca.writer-report", state: "running", last_exit_code: 7 },
      { label: "ai.anicca.x402-monitor", state: "not_running", last_exit_code: -9 },
    ],
  }));
  assert.equal(inventory.result, "pass");
  assert.deepEqual(inventory.runtime_observations.map((item) => item.last_exit_code), [7, -9]);
  const output = JSON.stringify(inventory);
  assert.doesNotMatch(output, /healthy|revenue|profit|balance|amount|currency/i);
  assert.ok(!Object.hasOwn(inventory, "health"));
});

test("source observations use injected existence checks and URI-like refs are not applicable", () => {
  const raw = structuredClone(canonicalRegistry);
  raw.financial_units[0].evidence_refs.push("https://example.com/life-manager");
  const registry = validateRegistry(raw);
  const calls = [];
  const observations = collectSourceObservations(registry, (ref) => {
    calls.push(ref);
    return ref === "docs/writer-agent/WRITER-AGENT-SSOT.md";
  });
  assert.ok(calls.includes("docs/writer-agent/WRITER-AGENT-SSOT.md"));
  assert.ok(!calls.includes("https://example.com/life-manager"));
  assert.ok(!calls.includes("launchd:ai.anicca.job-search-*"));
  assert.deepEqual(observations.find((item) => item.evidence_ref === "docs/writer-agent/WRITER-AGENT-SSOT.md"), {
    evidence_ref: "docs/writer-agent/WRITER-AGENT-SSOT.md", availability: "present",
  });
  assert.deepEqual(observations.find((item) => item.evidence_ref === "apps/x402-agents/package.json"), {
    evidence_ref: "apps/x402-agents/package.json", availability: "unavailable",
  });
  assert.deepEqual(observations.find((item) => item.evidence_ref === "launchd:ai.anicca.job-search-*"), {
    evidence_ref: "launchd:ai.anicca.job-search-*", availability: "not_applicable",
  });
  assert.deepEqual(observations.find((item) => item.evidence_ref === "https://example.com/life-manager"), {
    evidence_ref: "https://example.com/life-manager", availability: "not_applicable",
  });
  assert.deepEqual(observations.map((item) => item.evidence_ref), [...observations].map((item) => item.evidence_ref).sort());
});

test("receipt keeps only present unit evidence and no raw source payload", () => {
  const inventory = buildInventory(makeInput(["ai.anicca.writer-report"], canonicalRegistry, {
    sourceObservations: [
      { evidence_ref: "docs/writer-agent/WRITER-AGENT-SSOT.md", availability: "present", raw_payload: "secret" },
      { evidence_ref: "apps/x402-agents/package.json", availability: "unavailable", raw_payload: { token: "secret" } },
      { evidence_ref: "launchd:ai.anicca.job-search-*", availability: "not_applicable", payload: "secret" },
    ],
  }));
  const writer = inventory.financial_units.find((unit) => unit.financial_unit_id === "writer_agent");
  const x402 = inventory.financial_units.find((unit) => unit.financial_unit_id === "x402_services");
  assert.deepEqual(writer.source_evidence_refs, ["docs/writer-agent/WRITER-AGENT-SSOT.md"]);
  assert.deepEqual(x402.source_evidence_refs, []);
  assert.doesNotMatch(JSON.stringify(inventory), /raw_payload|secret|payload/);
  assert.ok(inventory.source_observations.every((item) => Object.keys(item).sort().join(",") === "availability,evidence_ref"));
});

test("normalizeLaunchctlList maps process state, exit status, filters, and sorts", () => {
  const stdout = [
    "PID Status Label",
    "- 7 ai.anicca.x402-monitor",
    "123 0 ai.anicca.writer-report",
    "unknown nope ai.anicca.unknown",
    "123 0 com.apple.other",
    "",
  ].join("\n");
  assert.deepEqual(normalizeLaunchctlList(stdout), [
    { label: "ai.anicca.unknown", state: "unknown", last_exit_code: null },
    { label: "ai.anicca.writer-report", state: "running", last_exit_code: 0 },
    { label: "ai.anicca.x402-monitor", state: "not_running", last_exit_code: 7 },
  ]);
});

test("observation hash is canonical and excludes receipt metadata", () => {
  const core = { b: [2, 1], a: { y: false, x: 1 } };
  assert.equal(observationHash(core), sha256Canonical(core));
  const first = buildInventory(makeInput(["ai.anicca.writer-report"]));
  const second = buildInventory(makeInput(["ai.anicca.writer-report"], canonicalRegistry, {
    generatedAt: "2027-01-01T00:00:00.000Z",
    inventoryId: "00000000-0000-4000-8000-000000000099",
  }));
  assert.equal(first.observation_hash, second.observation_hash);
  assert.notEqual(first.generated_at, second.generated_at);
  assert.notEqual(first.inventory_id, second.inventory_id);
});
