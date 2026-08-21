import assert from "node:assert/strict";
import { test } from "node:test";
import { authorizeSpend, computeSpendable, graduationGate } from "./treasury-policy.mjs";

test("computeSpendable subtracts reserve and committed liabilities and clamps at zero", () => {
  assert.equal(computeSpendable({ liquidUsdc: 10, reserveUsdc: 2, committedUsdc: 1.5 }), 6.5);
  assert.equal(computeSpendable({ liquidUsdc: 1, reserveUsdc: 2, committedUsdc: 0 }), 0);
});

test("authorizeSpend permits an amount inside both treasury and session caps", () => {
  assert.deepEqual(authorizeSpend({
    amountUsdc: 0.4, liquidUsdc: 2, reserveUsdc: 1, committedUsdc: 0,
    sessionSpentUsdc: 0.2, sessionCapUsdc: 1,
  }), { allowed: true, reason: "ok", spendableUsdc: 1, sessionRemainingUsdc: 0.4 });
});

test("authorizeSpend rejects a spend that crosses the reserve floor", () => {
  assert.equal(authorizeSpend({
    amountUsdc: 1.1, liquidUsdc: 2, reserveUsdc: 1, sessionSpentUsdc: 0, sessionCapUsdc: 2,
  }).reason, "reserve-floor");
});

test("authorizeSpend rejects a spend that crosses the session cap", () => {
  assert.equal(authorizeSpend({
    amountUsdc: 0.6, liquidUsdc: 10, reserveUsdc: 1, sessionSpentUsdc: 0.5, sessionCapUsdc: 1,
  }).reason, "session-cap");
});

test("authorizeSpend fails closed on malformed or missing caps", () => {
  assert.equal(authorizeSpend({ amountUsdc: 0.1, liquidUsdc: 10, reserveUsdc: 1 }).reason, "invalid-input");
  assert.equal(authorizeSpend({ amountUsdc: -1, liquidUsdc: 10, reserveUsdc: 1, sessionCapUsdc: 1 }).reason, "invalid-input");
});

test("graduationGate passes only with 1.5x coverage, 30-day runway, and zero human inference", () => {
  assert.deepEqual(graduationGate({
    externalRealizedNet30d: 15, computeCost30d: 6, shelterCost30d: 4,
    liquidRunwayDays: 30, humanPaidInference30d: 0,
  }), { eligible: true, reason: "ok", coverage: 1.5 });
});

test("graduationGate rejects human-paid inference and insufficient coverage/runway", () => {
  assert.equal(graduationGate({ externalRealizedNet30d: 20, computeCost30d: 5, shelterCost30d: 5, liquidRunwayDays: 30, humanPaidInference30d: 0.01 }).reason, "human-paid-inference");
  assert.equal(graduationGate({ externalRealizedNet30d: 10, computeCost30d: 8, shelterCost30d: 4, liquidRunwayDays: 30, humanPaidInference30d: 0 }).reason, "insufficient-coverage");
  assert.equal(graduationGate({ externalRealizedNet30d: 20, computeCost30d: 5, shelterCost30d: 5, liquidRunwayDays: 29, humanPaidInference30d: 0 }).reason, "insufficient-runway");
});
