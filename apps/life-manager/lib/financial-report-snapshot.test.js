"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildFinancialSnapshot,
  periodBounds,
  usdMicrosFromDecimal,
} = require("./financial-report-snapshot.js");

const WALLET = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
const NOW = Date.parse("2026-07-27T11:05:00.000Z"); // Monday 20:05 JST

function earning(kind, amountMinor, overrides = {}) {
  return {
    entry_key: `${kind}:${amountMinor}:${overrides.suffix || "a"}`,
    wallet_address: WALLET,
    kind,
    amount_minor: amountMinor,
    currency: "USD",
    occurred_at: "2026-07-27T10:00:00.000Z",
    source: "x402_sale",
    ...overrides,
  };
}

function cost(estUsd, overrides = {}) {
  return {
    ts: "2026-07-27T10:30:00.000Z",
    kind: "gemini_live",
    est_usd: estUsd,
    ...overrides,
  };
}

function snapshot(overrides = {}) {
  const earningsRows = overrides.earningsRows || [];
  const costRows = overrides.costRows || [];
  return buildFinancialSnapshot({
    kind: "daily",
    nowMs: NOW,
    timezone: "Asia/Tokyo",
    walletAddress: WALLET,
    onchainUsdcAtomic: "42000000",
    earningsRows,
    costRows,
    allTimeEarningsRows: overrides.allTimeEarningsRows || earningsRows,
    allTimeCostRows: overrides.allTimeCostRows || costRows,
    ...overrides,
  });
}

test("daily and weekly periods use the user's timezone and a half-open as-of boundary", () => {
  const daily = periodBounds({ kind: "daily", nowMs: NOW, timezone: "Asia/Tokyo" });
  assert.deepEqual(daily, {
    period_key: "2026-07-27",
    period_start: "2026-07-26T15:00:00.000Z",
    period_end: "2026-07-27T11:05:00.000Z",
  });

  const weekly = periodBounds({ kind: "weekly", nowMs: NOW, timezone: "Asia/Tokyo" });
  assert.deepEqual(weekly, {
    period_key: "2026-W31",
    period_start: "2026-07-26T15:00:00.000Z",
    period_end: "2026-07-27T11:05:00.000Z",
  });
});

test("cost decimals become conservative integer USD micros without float summation", () => {
  assert.equal(usdMicrosFromDecimal("0.003"), 3000n);
  assert.equal(usdMicrosFromDecimal(0.1), 100000n);
  assert.equal(usdMicrosFromDecimal("0.0000001"), 1n, "sub-micro cost rounds up, never down");
  assert.equal(usdMicrosFromDecimal("12.3456789"), 12345679n);
  assert.throws(() => usdMicrosFromDecimal("-0.01"), /non-negative/i);
  assert.throws(() => usdMicrosFromDecimal("not-money"), /decimal/i);
});

test("one snapshot sums verified revenue, losses, fees, API cost, and transfers without hiding a loss", () => {
  const result = snapshot({
    earningsRows: [
      earning("financial_external_income", 1_000),
      earning("financial_realized_loss", 315, { source: "polymarket", suffix: "loss" }),
      earning("financial_fee", 25, { source: "x402_sale", suffix: "fee" }),
      earning("financial_user_transfer", 100, { source: "payout", suffix: "payout" }),
      earning("financial_deposit", 999_999, { source: "bootstrap", suffix: "seed" }),
    ],
    costRows: [cost("0.003"), cost("0.0000001", { kind: "telnyx_call" })],
  });

  assert.equal(result.gross_usd_micros, "10000000");
  assert.equal(result.realized_loss_usd_micros, "3150000");
  assert.equal(result.financial_fee_usd_micros, "250000");
  assert.equal(result.api_cost_usd_micros, "3001");
  assert.equal(result.user_transfer_usd_micros, "1000000");
  assert.equal(result.operating_net_usd_micros, "6596999");
  assert.equal(result.excluded_rows, 1);
  assert.equal(result.balance_usdc_atomic, "42000000");
  assert.equal(result.stop_reason, "running");
});

test("a fractional-cent TaskMarket award stays exact through snapshot and payout capacity", () => {
  const result = snapshot({
    onchainUsdcAtomic: "38000000",
    earningsRows: [earning("financial_external_income", undefined, {
      source: "taskmarket_work",
      amount_atomic: "2312500",
      amount_decimals: 6,
      suffix: "taskmarket",
    })],
  });

  assert.equal(result.gross_usd_micros, "2312500");
  assert.equal(result.operating_net_usd_micros, "2312500");
  assert.equal(result.distributable_usdc_atomic, "2312500");
  assert.deepEqual(result.rail_pnl, [{
    rail: "WORK",
    gross_usd_micros: "2312500",
    realized_loss_usd_micros: "0",
    financial_fee_usd_micros: "0",
    user_transfer_usd_micros: "0",
    net_usd_micros: "2312500",
  }]);
});

test("seed, self-funding, internal moves, unverified rows, and the period end never become gross", () => {
  const result = snapshot({
    earningsRows: [
      earning("financial_deposit", 100, { suffix: "deposit" }),
      earning("financial_self_funding", 100, { suffix: "self" }),
      earning("financial_internal_move", 100, { suffix: "move" }),
      earning("financial_unverified", 100, { suffix: "unverified" }),
      earning("financial_external_income", 100, {
        suffix: "at-end",
        occurred_at: new Date(NOW).toISOString(),
      }),
    ],
  });

  assert.equal(result.gross_usd_micros, "0");
  assert.equal(result.operating_net_usd_micros, "0");
  assert.equal(result.excluded_rows, 4);
  assert.equal(result.stop_reason, "no_external_income");
});

test("weekly rail P&L keeps SELL, WORK, CAPITAL, and unclassified evidence separate", () => {
  const result = snapshot({
    kind: "weekly",
    earningsRows: [
      earning("financial_external_income", 300, { source: "x402_sale", suffix: "sell" }),
      earning("financial_external_income", 200, { source: "x402_work", suffix: "work" }),
      earning("financial_realized_loss", 150, { source: "polymarket", suffix: "capital" }),
      earning("financial_fee", 25, { source: "other", suffix: "other" }),
    ],
  });

  assert.deepEqual(result.rail_pnl.map((row) => [row.rail, row.net_usd_micros]), [
    ["CAPITAL", "-1500000"],
    ["SELL", "3000000"],
    ["UNCLASSIFIED", "-250000"],
    ["WORK", "2000000"],
  ]);
});

test("self-funded ratio is measured from positive verified net over recorded compute cost", () => {
  const measured = snapshot({
    earningsRows: [earning("financial_external_income", 100)],
    costRows: [cost("0.25")],
  });
  assert.equal(measured.self_funded_bps, 40000);
  assert.equal(measured.self_funded_status, "measured");

  const losing = snapshot({
    earningsRows: [earning("financial_realized_loss", 100)],
    costRows: [],
  });
  assert.equal(losing.self_funded_bps, 0);
  assert.equal(losing.self_funded_status, "non_positive_net");
  assert.equal(losing.stop_reason, "negative_net");

  const missingCost = snapshot({
    earningsRows: [earning("financial_external_income", 100)],
    costRows: [],
  });
  assert.equal(missingCost.self_funded_bps, null);
  assert.equal(missingCost.self_funded_status, "operating_cost_unmeasured");
});

test("distributable uses all-time rows and all-time API cost while period totals stay local", () => {
  const oldIncome = earning("financial_external_income", 10_000, {
    suffix: "old",
    occurred_at: "2026-07-20T10:00:00.000Z",
  });
  const result = snapshot({
    earningsRows: [],
    costRows: [],
    allTimeEarningsRows: [oldIncome],
    allTimeCostRows: [cost("1.25", { ts: "2026-07-20T10:30:00.000Z" })],
    onchainUsdcAtomic: "100000000",
  });

  assert.equal(result.gross_usd_micros, "0");
  assert.equal(result.distributable_usdc_atomic, "63750000");
  assert.equal(result.payout_reason, "ready");
});

test("mixed wallets, non-USD ledger money, and absent measured balance fail closed", () => {
  assert.throws(() => snapshot({
    earningsRows: [earning("financial_external_income", 100, {
      wallet_address: "0x6592aA47cCAc10031253551d3Cc30fc64bA7EDc7",
    })],
  }), /wallet/i);
  assert.throws(() => snapshot({
    earningsRows: [earning("financial_external_income", 100, { currency: "JPY" })],
  }), /USD/i);
  assert.throws(() => snapshot({ onchainUsdcAtomic: null }), /balance/i);
});
