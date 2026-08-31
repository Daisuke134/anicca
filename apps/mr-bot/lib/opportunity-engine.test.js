"use strict";
// 10h BRAIN-b contract: closed candidate schema + gate ordering guarantees.
// The full 18-case decision matrix lives in eval/intent-cases.jsonl
// (eval/run-intent-eval.js); these tests pin the schema and the two
// definite-good invariants that must hold regardless of the other factors.

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateCandidate, decideOpportunity, CATEGORIES, LEVELS } = require("./opportunity-engine.js");
const { confidenceForTier } = require("./intent-graph.js");

const NOW_MS = Date.parse("2026-07-24T09:00:00.000Z");

function intent(overrides = {}) {
  return {
    id: "i-1", uid: "u-1", kind: "explicit_goal", statement: "goal",
    provenance: { source: "user_message", evidence: "e", observedAt: "2026-07-01T00:00:00.000Z" },
    confidenceTier: "explicit", confidence: confidenceForTier("explicit"),
    expiresAt: null, status: "active", supersedes: null,
    ...overrides,
  };
}

function candidate(overrides = {}) {
  return {
    id: "c-1", category: "life_admin", description: "candidate",
    benefit: "high", urgency: "medium", cost: "low", risk: "low",
    reversible: true, supportsIntentIds: ["i-1"], violatesIntentIds: [],
    delegationId: null, materialPreference: false, previouslyAsked: false,
    ...overrides,
  };
}

test("schema: closed keys and enums", () => {
  assert.deepEqual([...CATEGORIES], ["body", "mind", "finance", "life_admin"]);
  assert.deepEqual([...LEVELS], ["low", "medium", "high"]);
  assert.doesNotThrow(() => validateCandidate(candidate()));
  assert.throws(() => validateCandidate({ ...candidate(), extra: 1 }), /unknown key/);
  assert.throws(() => validateCandidate(candidate({ category: "social" })), /category/);
  assert.throws(() => validateCandidate(candidate({ benefit: "huge" })), /benefit/);
  assert.throws(() => validateCandidate(candidate({ reversible: "yes" })), /reversible/);
  assert.throws(() => validateCandidate(candidate({ supportsIntentIds: [""] })), /supportsIntentIds/);
  assert.throws(() => validateCandidate(candidate({ materialPreference: "no" })), /materialPreference/);
});

test("definite good: an active prohibition beats every other factor, even a perfect candidate", () => {
  const graph = [intent(), intent({ id: "p-1", kind: "prohibition", statement: "do not" })];
  const perfect = candidate({ violatesIntentIds: ["p-1"], delegationId: null });
  assert.deepEqual(decideOpportunity(graph, perfect, NOW_MS), { decision: "skip", reason: "prohibition:p-1" });
});

test("definite good: zero active supporting intent means doing nothing, never acting on a hunch", () => {
  const corrected = intent({ id: "i-corr", status: "corrected", confidenceTier: "inferred", confidence: confidenceForTier("inferred") });
  const out = decideOpportunity([corrected], candidate({ supportsIntentIds: ["i-corr"] }), NOW_MS);
  assert.deepEqual(out, { decision: "skip", reason: "no-active-supporting-intent" });
});

test("gate: delegated + reversible + low risk acts without asking; losing any one of the three asks", () => {
  const graph = [intent(), intent({ id: "d-1", kind: "delegation", statement: "delegate research" })];
  const acts = decideOpportunity(graph, candidate({ delegationId: "d-1" }), NOW_MS);
  assert.equal(acts.decision, "act");
  const noDelegation = decideOpportunity(graph, candidate({ delegationId: null }), NOW_MS);
  assert.equal(noDelegation.decision, "ask");
  const irreversible = decideOpportunity(graph, candidate({ delegationId: "d-1", reversible: false }), NOW_MS);
  assert.deepEqual(irreversible, { decision: "ask", reason: "irreversible-needs-consent" });
});
