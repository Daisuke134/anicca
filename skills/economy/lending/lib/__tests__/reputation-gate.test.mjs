// node:test — lending/lib/reputation-gate.mjs (franklin-reputation-gasless G3, RED phase). JS port of
// Azeth/UFX's ReputationGateHook.beforeAction (23 §11 部品3) -- `getSummaryFn` is dependency-injected
// (defaults to the real gig/lib/reputation.mjs::getReputationSummary in production), so these tests
// exercise the threshold-composition/fail-open decision logic only, no real network call.
import { test } from "node:test";
import assert from "node:assert/strict";
import { passesOnchainReputationGate } from "../reputation-gate.mjs";

test("★G3 spec★ unset thresholds (minScore<=0 AND minJobCount<=0) -> fail-open passthrough, getSummaryFn is NEVER called (段階導入)", async () => {
  let called = false;
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    getSummaryFn: async () => {
      called = true;
      return { ok: true, count: 0, summaryValue: 0 };
    },
  });
  assert.equal(result.eligible, true);
  assert.equal(called, false, "an unset gate must never even attempt a network read");
});

test("passesOnchainReputationGate: borrower meets both thresholds -> eligible:true", async () => {
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    minScore: 50,
    minJobCount: 3,
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    getSummaryFn: async () => ({ ok: true, count: 5, summaryValue: 90 }),
  });
  assert.equal(result.eligible, true);
});

test("★azeth-parity★ passesOnchainReputationGate: insufficient job count -> eligible:false, reason names the shortfall", async () => {
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    minScore: 0,
    minJobCount: 3,
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    getSummaryFn: async () => ({ ok: true, count: 1, summaryValue: 999 }),
  });
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "insufficient_job_count");
});

test("★azeth-parity★ passesOnchainReputationGate: insufficient score -> eligible:false", async () => {
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    minScore: 80,
    minJobCount: 0,
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    getSummaryFn: async () => ({ ok: true, count: 10, summaryValue: 10 }),
  });
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "insufficient_score");
});

test("no borrowerAgentId with a gate configured -> eligible:false (fail-closed on the identity gap, not fail-open)", async () => {
  const result = await passesOnchainReputationGate({
    borrowerAgentId: null,
    minScore: 50,
    getSummaryFn: async () => ({ ok: true, count: 10, summaryValue: 90 }),
  });
  assert.equal(result.eligible, false);
});

test("★MONEY-SAFETY fail-open★ getSummaryFn read failure (network down) -> eligible:true, never blocks lending on a reputation outage", async () => {
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    minScore: 50,
    minJobCount: 1,
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    getSummaryFn: async () => ({ ok: false, reason: "network down" }),
  });
  assert.equal(result.eligible, true);
  assert.match(result.reason, /fail_open/);
});

test("★MONEY-SAFETY fail-open★ a gate configured but no clientAddresses provided -> eligible:true (cannot evaluate, never blocks)", async () => {
  let called = false;
  const result = await passesOnchainReputationGate({
    borrowerAgentId: "5",
    minScore: 50,
    clientAddresses: [],
    getSummaryFn: async () => {
      called = true;
      return { ok: true, count: 10, summaryValue: 90 };
    },
  });
  assert.equal(result.eligible, true);
  assert.equal(called, false);
});
