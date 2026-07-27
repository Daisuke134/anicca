"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { computePayout } = require("./payout-policy.js");

const WALLET = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";

function earning(kind, amountMinor, overrides = {}) {
  return {
    entry_key: `${kind}:${amountMinor}:${overrides.suffix || "a"}`,
    wallet_address: WALLET,
    kind,
    amount_minor: amountMinor,
    currency: "USD",
    occurred_at: "2026-07-27T12:00:00.000Z",
    ...overrides,
  };
}

test("verified profit pays only the balance above the $35 survival reserve", () => {
  const result = computePayout({
    rows: [
      earning("financial_external_income", 10_000),
      earning("financial_fee", 500),
      earning("financial_user_transfer", 1_000),
    ],
    walletAddress: WALLET,
    onchainUsdcAtomic: "42000000",
  });

  assert.deepEqual(result, {
    amountAtomic: "7000000",
    verifiedSurplusMinor: 8500,
    reason: "ready",
    reserveAtomic: "35000000",
  });
});

test("bootstrap deposits, self-funding, internal moves, and unverified rows never create payout capacity", () => {
  const rows = [
    earning("financial_deposit", 100_000, { suffix: "deposit" }),
    earning("financial_self_funding", 100_000, { suffix: "self" }),
    earning("financial_internal_move", 100_000, { suffix: "internal" }),
    earning("financial_unverified", 100_000, { suffix: "unverified" }),
  ];
  const result = computePayout({
    rows,
    walletAddress: WALLET,
    onchainUsdcAtomic: "1000000000",
  });

  assert.equal(result.amountAtomic, "0");
  assert.equal(result.verifiedSurplusMinor, 0);
  assert.equal(result.reason, "no_verified_surplus");
});

test("realized losses and fees reduce distributable profit without becoming negative money", () => {
  const result = computePayout({
    rows: [
      earning("financial_external_income", 500),
      earning("financial_realized_loss", 700),
      earning("financial_fee", 50),
    ],
    walletAddress: WALLET,
    onchainUsdcAtomic: "1000000000",
  });

  assert.equal(result.amountAtomic, "0");
  assert.equal(result.verifiedSurplusMinor, 0);
  assert.equal(result.reason, "no_verified_surplus");
});

test("the explicit transaction cap is a third independent upper bound", () => {
  const result = computePayout({
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "100000000",
    maxPayoutAtomic: "5000000",
  });

  assert.equal(result.amountAtomic, "5000000");
  assert.equal(result.reason, "ready");
});

test("a balance at or below the reserve produces an honest no-op", () => {
  const result = computePayout({
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "35000000",
  });

  assert.equal(result.amountAtomic, "0");
  assert.equal(result.reason, "reserve_floor");
});

test("sub-cent balance dust stays in the agent wallet because the append-only ledger records exact cents", () => {
  const result = computePayout({
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "42000001",
  });

  assert.equal(result.amountAtomic, "7000000");
});

test("a caller may raise the survival reserve but may never silently lower it", () => {
  const raised = computePayout({
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "50000000",
    reserveAtomic: "46000000",
  });
  assert.equal(raised.amountAtomic, "4000000");
  assert.equal(raised.reserveAtomic, "46000000");

  assert.throws(() => computePayout({
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "50000000",
    reserveAtomic: "34999999",
  }), /reserve/i);
});

test("another wallet's row and non-USD money fail closed instead of funding this tenant", () => {
  assert.throws(() => computePayout({
    rows: [earning("financial_external_income", 10_000, {
      wallet_address: "0x6592aA47cCAc10031253551d3Cc30fc64bA7EDc7",
    })],
    walletAddress: WALLET,
    onchainUsdcAtomic: "100000000",
  }), /wallet/i);

  assert.throws(() => computePayout({
    rows: [earning("financial_external_income", 10_000, { currency: "JPY" })],
    walletAddress: WALLET,
    onchainUsdcAtomic: "100000000",
  }), /USD/i);
});

test("all atomic inputs are exact non-negative integers", () => {
  const base = {
    rows: [earning("financial_external_income", 10_000)],
    walletAddress: WALLET,
  };
  assert.throws(() => computePayout({ ...base, onchainUsdcAtomic: "42.1" }), /integer/i);
  assert.throws(() => computePayout({ ...base, onchainUsdcAtomic: "-1" }), /integer/i);
  assert.throws(() => computePayout({
    ...base,
    onchainUsdcAtomic: "100000000",
    maxPayoutAtomic: "1.2",
  }), /integer/i);
});
